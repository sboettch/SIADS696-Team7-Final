#!/usr/bin/env python3
"""
Rewrite the SIADS 696 Google Doc with all rubric gaps addressed.
v3: Uses multi-pass approach — text first, then tables inserted by reading doc state.
"""
import os, json, time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'token.json')
DOC_INFO = os.path.join(SCRIPT_DIR, 'gdoc_info.json')
IMAGE_IDS = os.path.join(SCRIPT_DIR, 'gdoc_image_ids.json')

FONT = 'Arial'
SZ = 11


def get_services():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE)
    return build('docs', 'v1', credentials=creds)


def clear_doc(docs, doc_id):
    doc = docs.documents().get(documentId=doc_id).execute()
    end = doc['body']['content'][-1]['endIndex']
    if end > 2:
        docs.documents().batchUpdate(documentId=doc_id, body={'requests': [
            {'deleteContentRange': {'range': {'startIndex': 1, 'endIndex': end - 1}}}
        ]}).execute()


def style_req(start, end, bold=False, italic=False, size=SZ):
    return {'updateTextStyle': {
        'range': {'startIndex': start, 'endIndex': end},
        'textStyle': {
            'bold': bold, 'italic': italic,
            'fontSize': {'magnitude': size, 'unit': 'PT'},
            'weightedFontFamily': {'fontFamily': FONT},
        },
        'fields': 'bold,italic,fontSize,weightedFontFamily',
    }}


def para_req(start, end, named):
    return {'updateParagraphStyle': {
        'range': {'startIndex': start, 'endIndex': end},
        'paragraphStyle': {'namedStyleType': named},
        'fields': 'namedStyleType',
    }}


def align_req(start, end, alignment):
    return {'updateParagraphStyle': {
        'range': {'startIndex': start, 'endIndex': end},
        'paragraphStyle': {'alignment': alignment},
        'fields': 'alignment',
    }}


class Writer:
    """Accumulates text into a single string, tracks style/heading ranges, then flushes."""

    def __init__(self):
        self.text_parts = []
        self.styles = []      # (offset, length, bold, italic, size)
        self.headings = []     # (offset, length, level)
        self.aligns = []       # (offset, length, alignment)
        self.images = []       # (offset_after_text, uri, width)
        self.table_markers = []  # (marker_text, headers, rows)
        self._pos = 0

    def _add(self, t, bold=False, italic=False, size=SZ):
        self.styles.append((self._pos, len(t), bold, italic, size))
        self.text_parts.append(t)
        self._pos += len(t)

    def heading(self, t, level=1):
        sz = {1: 14, 2: 12, 3: 11}.get(level, 11)
        start = self._pos
        self._add(t + '\n', bold=True, size=sz)
        self.headings.append((start, len(t) + 1, level))

    def para(self, t):
        self._add(t + '\n')

    def line(self, t, **kw):
        self._add(t + '\n', **kw)

    def nl(self):
        self._add('\n')

    def caption(self, t):
        self._add(t + '\n', italic=True, size=10)

    def bullet(self, t):
        self._add('\u2022 ' + t + '\n')

    def center_block_start(self):
        self._center_start = self._pos

    def center_block_end(self):
        self.aligns.append((self._center_start, self._pos - self._center_start, 'CENTER'))

    def image_placeholder(self, uri, width=400):
        marker = f'[IMG_{len(self.images):02d}]'
        self.images.append((marker, uri, width))
        self._add(marker + '\n')

    def table_placeholder(self, headers, rows):
        marker = f'[TBL_{len(self.table_markers):02d}]'
        self.table_markers.append((marker, headers, rows))
        self._add(marker + '\n')

    def get_full_text(self):
        return ''.join(self.text_parts)

    def build_text_requests(self):
        """Build requests to insert text at index 1 and apply all formatting."""
        reqs = []
        full = self.get_full_text()
        # Insert all text at once
        reqs.append({'insertText': {'location': {'index': 1}, 'text': full}})
        # Apply styles (offset 0 in our text = index 1 in the doc)
        for offset, length, bold, italic, size in self.styles:
            reqs.append(style_req(1 + offset, 1 + offset + length, bold, italic, size))
        # Apply heading paragraph styles
        for offset, length, level in self.headings:
            reqs.append(para_req(1 + offset, 1 + offset + length, f'HEADING_{level}'))
        # Apply alignments
        for offset, length, align in self.aligns:
            reqs.append(align_req(1 + offset, 1 + offset + length, align))
        return reqs


def build_content(images):
    w = Writer()

    def img(f):
        return images.get(f, {}).get('uri', '')

    # Title
    w.center_block_start()
    w.line('SIADS 696 Milestone II Project Report', bold=True, size=16)
    w.line('Frequent Mental Distress Prediction Using Air Pollution', bold=True, size=13)
    w.line('Sophia Boettcher (sboettch@umich.edu), Jaeah Kim (jaeah@umich.edu), Kyle Rodriguez (kylerod@umich.edu)')
    w.center_block_end()
    w.nl()

    # Introduction
    w.heading('Introduction', 1)
    w.para('The motivation behind this project aims to utilize previous findings from related literature and leverage supervised and unsupervised learning to answer two questions: (1) Can a county\u2019s air quality and profile reliably predict its mental health needs next year? (2) Do high pollution or high distress clusters share common geographic or industrial traits? Note that we do not aim to claim causality; we are conducting a predictive and exploratory exercise.')
    w.para('It\u2019s well-known beyond anecdote that health outcomes are influenced by many environmental, economic, and social factors; yet, it remains unclear whether on a population-level (here, using county-level characteristics), if we can use data to anticipate future community mental health needs. Our project investigates whether annual air quality, climate, and socioeconomic conditions can predict next-year Frequent Mental Distress (FMD), defined by the CDC PLACES dataset as the percentage of adults reporting poor mental health for 14 or more days in the past month. As part of our project, we also explore if counties naturally group/cluster into distinct environmental and socioeconomic profiles along differing mental health outcomes.')
    w.para('If community mental health needs can be predicted even modestly, public health agencies could better allocate resources and identify at-risk regions pre-emptively. Understanding the limits of county-level data helps identify what additional information may be needed for reliable forecasting. Our work also provides an integrated county-year dataset that can support future research on environmental determinants of mental health.')
    w.para('A growing body of literature suggests that air pollution, climate, and socioeconomic conditions are associated with mental health outcomes, but relatively few studies have examined whether these variables can predict future community-level mental distress using machine learning. We were interested in evaluating whether publicly available environmental and demographic data contain enough predictive signal to forecast next-year mental health and whether unsupervised learning could reveal meaningful county profiles beyond traditional statistical analyses.')
    w.para('The primary objective was to construct a predictive framework based on a county\u2019s current socio-environmental and economic ecosystem. The target variable was defined as Next-Year FMD prevalence. We constructed an enriched county-year panel containing 14,748 observations across 3,008 U.S. counties from 2019\u20132023 by combining data from CDC PLACES, EPA AirData, NOAA climate records, the American Community Survey (ACS), and Census county geographies.')
    w.para('Predicting public health outcomes within a spatial panel structure introduces a critical methodological challenge: temporal data leakage. To address this, our supervised learning design employed a leakage-safe forecasting framework in which features from year t were used to predict FMD in year t + 1. We evaluated multiple regression models, including Elastic Net, Random Forest, Gradient Boosting, and XGBoost, using cross-validation and a held-out test set.')
    w.para('For the unsupervised learning component, we standardized all non-FMD variables and applied DBSCAN clustering to a low-dimensional embedding. FMD was intentionally excluded during clustering and reintroduced afterward to compare mental health outcomes across the discovered clusters.')
    w.para('The best supervised model was a tuned Random Forest, achieving a holdout RMSE of 1.98 and MAE of 1.65, compared with the Dummy Regressor baseline RMSE of 2.43. Holdout R\u00b2 remained negative (\u22120.02). The unsupervised analysis revealed one dominant cluster along with several smaller outlier clusters. We conclude that while the existing body of county-level data is currently limited for predicting future FMD, it remains a valuable starting point for future exploratory profiling and generating new hypotheses.')

    # Related Work
    w.heading('Related Work', 1)
    w.para('There is an extensive and rapidly growing body of research dedicated to the environmental determinants of mental health at the community and county levels in the United States. "Particulate matters (PM2.5, PM10) and the risk of depression among middle-aged and older population" (Park, et al.) found that prolonged exposure of particulate matters increased risk of depression in the elderly. "The impact of neighborhood environment on mental health: Evidence from China" (Lei, et al.) concluded that air pollution perception, coupled with socioeconomic status, was crucial for mental health in Chinese communities. The Gulf Long-Term Follow-up Study (Werder et al., 2024) explored how PM2.5 and greenspace impact depression in the Southeastern U.S.')
    w.para('Our project extends this prior work in two key ways. First, rather than focusing on specific age cohorts or geographic regions, we model county-level outcomes across the entire contiguous United States. Second, we incorporate unsupervised learning to uncover latent socio-environmental archetypes across U.S. counties. This project also builds on our own prior Milestone I work, which initially explored the relationship between air quality and health outcomes and motivated the expanded scope of the current analysis.')

    # Data Sources
    w.heading('Data Sources', 1)
    w.para('This project utilizes data from five sources: CDC PLACES, EPA AirData (annual and daily), the American Community Survey (ACS), NOAA Climate at a Glance, and Census county boundary shapefiles. The modeling panel is county-year and uses five-digit county GEOID as the primary merge key.')
    w.nl()
    w.caption('Table 1. Datasets used for analysis.')
    w.table_placeholder(
        ['Source', 'Format', 'Key Variables', 'Coverage', 'Records'],
        [['CDC PLACES', 'CSV', 'FMD prevalence, CIs', '2018\u20132023', '~18K county-yr'],
         ['EPA AirData Annual', 'CSV', 'AQI days, Max/Median AQI', '2019\u20132023', '~6.5K county-yr'],
         ['EPA AirData Daily', 'ZIP/CSV', 'Daily AQI mean, SD, p90', '2019\u20132023', '~5.4M daily'],
         ['ACS 5-Year', '.dat', 'Income, poverty, education', '2019\u20132023', '~3.1K \u00d7 5'],
         ['NOAA Climate', 'JSON', 'Temp, precip, anomalies', '2019\u20132023', '~3.1K \u00d7 5'],
         ['Census Boundaries', 'Shapefile', 'County polygons', '2023', '3,234 polygons']])
    w.nl()
    w.para('Our enriched dataset contains 83 columns. The final harmonized panel contains 14,748 county-year observations across 3,008 counties. EPA daily AQI features cover only counties with daily monitor reporting, so many missing daily features are imputed.')

    # Feature Engineering
    w.heading('Feature Engineering', 1)
    w.para('Since we were analyzing data from multiple datasets, we merged them into a single table by state and county name. We noticed many rows were missing environmental measurements from AirData. For this imputation, we used a BallTree to perform a K-nearest-neighbor algorithm to fill in missing values using the geographically nearest 10 points with valid AirData measurements, weighted by distance.')
    w.para('We converted scalar columns (population, number of unemployed people, etc.) into ratios (e.g. unemployment rate) to normalize the dataset. The original columns were dropped to prevent multicollinearity.')
    w.para('Finally, for each county, we shifted FMD forward one year so that current-year features predict next-year FMD, addressing data leakage. The final dataset was distilled to 14,748 records across 24 columns. A full list of features is provided in Appendix B.')

    # Supervised Learning
    w.heading('Supervised Learning', 1)
    w.para('The supervised task was a regression problem: predict next-year FMD prevalence. As a baseline, we chose a Dummy Regressor that always predicts the mean FMD.')
    w.para('We selected three model families to ensure diversity. ElasticNet was chosen because features such as poverty rate, uninsured rate, and unemployment rate likely exhibit multicollinearity, and ElasticNet\u2019s combined L1/L2 regularization handles this while performing implicit feature selection. Random Forest was selected to capture non-linear interactions \u2014 for example, the effect of air quality may differ by income level. Gradient Boosting (XGBoost) was chosen as a sequential ensemble method that iteratively corrects residual errors, complementing Random Forest\u2019s parallel averaging approach. This gives us bagging vs. boosting for comparison.')
    w.para('We performed hyperparameter tuning using GridSearchCV with 5-fold cross-validation. For Random Forest: n_estimators \u2208 {100, 250}, max_features \u2208 {sqrt, 0.5, 0.7, 1.0}, min_samples_leaf \u2208 {1, 3, 8, 15}. For Gradient Boosting: n_estimators \u2208 {100, 250}, max_depth \u2208 {3, 5}, learning_rate \u2208 {0.01, 0.1}. For ElasticNet: alpha \u2208 {0.01, 0.1, 1.0}, l1_ratio \u2208 {0.1, 0.5, 0.9}. The configuration with the lowest mean CV RMSE was selected.')

    # Evaluation
    w.heading('Evaluation', 2)
    w.para('We used RMSE, MAE, and R\u00b2 as evaluation metrics with grouped cross-validation by year. RMSE was primary because large errors are undesirable for a sensitive metric like FMD.')
    w.nl()
    if img('figure_01_supervised_model_comparison.png'):
        w.image_placeholder(img('figure_01_supervised_model_comparison.png'), 400)
    w.caption('Figure 1. Holdout performance across tuned model families. Random Forest achieves the lowest RMSE (1.98), demonstrating that non-linear tree-based methods capture county-level variation that ElasticNet\u2019s linear structure cannot, though all models remain near the Dummy baseline.')
    w.nl()
    w.caption('Table 2. Supervised model comparison. CV metrics report mean \u00b1 SD across 5 folds.')
    w.table_placeholder(
        ['Model', 'Holdout RMSE', 'Holdout MAE', 'Holdout R\u00b2', 'CV RMSE (mean \u00b1 SD)'],
        [['Random Forest tuned', '1.98', '1.65', '\u22120.02', '2.02 \u00b1 0.63'],
         ['Gradient Boosting tuned', '2.30', '1.91', '\u22120.37', '2.16 \u00b1 0.49'],
         ['ElasticNet tuned', '2.31', '1.97', '\u22120.38', '2.32 \u00b1 0.59'],
         ['Dummy mean baseline', '2.43', '1.95', '\u22120.54', '2.73 \u00b1 0.46']])

    # Findings
    w.heading('Findings', 2)
    w.para('The best model reduced RMSE by about 0.45 percentage points relative to the Dummy baseline. The negative R\u00b2 values indicate the model did not explain holdout variation better than a simple mean predictor under the strict temporal split.')
    w.nl()
    if img('figure_02_predictions_residuals.png'):
        w.image_placeholder(img('figure_02_predictions_residuals.png'), 450)
    w.caption('Figure 2. Predicted vs. actual next-year FMD (left) and residual distribution (right) for the 2022\u21922023 holdout. Predictions compress toward the mean, with systematic underprediction in the high-FMD tail.')

    # In-Depth Evaluation
    w.heading('In-Depth Evaluation', 2)
    w.heading('Feature Importance and Ablation', 3)
    w.nl()
    if img('figure_04_rf_feature_importance.png'):
        w.image_placeholder(img('figure_04_rf_feature_importance.png'), 420)
    w.caption('Figure 4. Impurity-based feature importance for Random Forest. Education and climate variables rank highest, while individual AQI pollutant days contribute less.')
    w.nl()
    w.caption('Table 3. Feature-family ablation results.')
    w.table_placeholder(
        ['Removed Family', 'Features Removed', 'Holdout RMSE', 'RMSE Delta'],
        [['Education & health access', '5', '2.06', '+0.08'],
         ['Industry composition', '13', '2.01', '+0.03'],
         ['Annual AQI', '15', '1.99', '+0.01'],
         ['None (full model)', '0', '1.98', '0.00'],
         ['Daily AQI exposure', '25', '1.98', '\u22120.00'],
         ['Socioeconomic scale', '9', '1.94', '\u22120.04'],
         ['Climate', '6', '1.94', '\u22120.04']])
    w.nl()
    if img('figure_05_rf_ablation.png'):
        w.image_placeholder(img('figure_05_rf_ablation.png'), 400)
    w.caption('Figure 5. Feature-family ablation. Removing education/health-access features causes the largest RMSE increase (+0.08), while removing daily AQI features slightly improves performance.')

    w.heading('Sensitivity Analysis', 3)
    w.caption('Table 4. Random Forest sensitivity analysis, top settings.')
    w.table_placeholder(
        ['min_samples_leaf', 'max_features', 'Holdout RMSE', 'Holdout R\u00b2'],
        [['1', 'sqrt', '1.98', '\u22120.02'], ['3', 'sqrt', '2.00', '\u22120.04'],
         ['8', 'sqrt', '2.02', '\u22120.06'], ['15', 'sqrt', '2.05', '\u22120.09'],
         ['1', '0.7', '2.06', '\u22120.10'], ['1', '0.5', '2.06', '\u22120.10']])
    w.nl()
    if img('figure_06_rf_sensitivity.png'):
        w.image_placeholder(img('figure_06_rf_sensitivity.png'), 400)
    w.caption('Figure 6. Sensitivity analysis. Smaller leaves with sqrt sampling consistently outperform.')
    w.nl()
    w.para('The tradeoff is interpretability and stability versus nonlinear flexibility: Random Forest performed best, but at the cost of reduced transparency relative to ElasticNet.')

    w.heading('Failure Analysis', 3)
    w.para('Our failure analysis identified three distinct failure categories:')
    w.nl()
    w.caption('Table 5. Failure analysis: largest prediction errors by category.')
    w.table_placeholder(
        ['County', 'State', 'Actual', 'Predicted', 'Residual', 'Category'],
        [['Roosevelt', 'MT', '22.70', '16.35', '+6.35', 'High-distress tail'],
         ['Big Horn', 'MT', '22.90', '16.74', '+6.16', 'High-distress tail'],
         ['Corson', 'SD', '21.90', '15.86', '+6.04', 'High-distress tail'],
         ['Marshall', 'WV', '23.00', '16.96', '+6.04', 'Appalachian structural'],
         ['Ohio', 'WV', '22.10', '16.22', '+5.88', 'Appalachian structural'],
         ['Wetzel', 'WV', '23.90', '18.07', '+5.83', 'Appalachian structural'],
         ['Mahnomen', 'MN', '21.50', '15.84', '+5.66', 'Indigenous reservation'],
         ['Rosebud', 'MT', '21.60', '16.01', '+5.59', 'Indigenous reservation']])
    w.nl()
    w.para('The three categories reflect distinct gaps: (1) High-distress tail underprediction in rural counties \u2014 fix: add healthcare provider density and disability data. (2) Appalachian structural underprediction where opioid crisis and sparse behavioral health compound \u2014 fix: add RUCC rurality codes, opioid burden. (3) Indigenous reservation underprediction in counties with tribal lands \u2014 fix: incorporate IHS service area data and tribal health indicators.')
    w.nl()
    if img('figure_03_residual_map.png'):
        w.image_placeholder(img('figure_03_residual_map.png'), 450)
    w.caption('Figure 3. Geographic distribution of supervised residuals. Underprediction concentrates in Appalachia, the Northern Plains, and the rural South.')

    # Unsupervised Learning
    w.heading('Unsupervised Learning', 1)
    w.heading('Methods and Motivation', 2)
    w.para('Our unsupervised analysis asked whether counties fall into distinct socio-environmental clusters. FMD was intentionally excluded from clustering so that DBSCAN and K-Means discovered structure using only environmental, climate, socioeconomic, healthcare access, education, and industry characteristics. We then examined FMD after clustering as a held-out descriptive outcome. This design prevents the cluster labels from simply reproducing the mental-health target and makes any FMD differences across clusters an external comparison rather than a clustering input.')
    w.para('Before clustering, numeric county-profile features were harmonized and standardized with StandardScaler so variables measured on different scales contributed comparably. The final reproducible report pipeline used PCA for the two-dimensional diagnostic embedding and cluster visualizations; earlier exploratory notebooks tested UMAP/PCA options, but the report figures and sensitivity table are generated from the PCA-based pipeline for reproducibility.')
    w.para('DBSCAN and K-Means were selected as complementary methods. DBSCAN was selected because it does not require pre-specifying the number of clusters and can identify outlier counties as noise. K-Means was used as a centroid-based comparison because it assigns every county to exactly one cluster, making it useful for interpretable county archetypes. In the final reproducible pipeline, DBSCAN searched exactly 70 parameter combinations: 14 eps values from np.round(np.linspace(0.15, 2.0, 14), 2) multiplied by five min_samples values {5, 10, 20, 35, 50}. The selected DBSCAN setting was eps = 1.43 and min_samples = 5. K-Means evaluated k in {2, 3, 4, 5, 6} and selected k = 2, which had the highest silhouette score (0.89 on the PCA embedding; 0.75 on the scaled feature matrix). The full unsupervised search output therefore contains 75 rows: 70 DBSCAN settings plus 5 K-Means settings.')
    w.para('Reproducibility references: DBSCAN/K-Means search code: https://github.com/sboettch/SIADS696-Team7-Final/blob/main/scripts/03_modeling/generate_rubric_analyses.py#L309-L365; generated search results: https://github.com/sboettch/SIADS696-Team7-Final/blob/main/outputs/modeling/rubric_completion/unsupervised_method_search.csv; Figure 11 generation code: https://github.com/sboettch/SIADS696-Team7-Final/blob/main/scripts/04_reporting_visualizations/create_reproducible_visualizations_notebook.py#L320-L348.')

    w.heading('Unsupervised Evaluation', 2)
    w.para('Silhouette scores were chosen because they measure both intra-cluster cohesion and inter-cluster separation without ground truth. We also used Calinski-Harabasz index for K-Means. Held-out FMD was compared via one-way ANOVA.')
    w.nl()
    w.caption('Table 6. Unsupervised method comparison.')
    w.table_placeholder(
        ['Method', 'Parameters', 'Clusters', 'Noise %', 'Sil. (emb)', 'Sil. (scaled)', 'CH'],
        [['DBSCAN', 'eps=1.43, min_s=5', '2', '2.2%', '0.76', '0.45', '\u2014'],
         ['KMeans', 'k=2', '2', '0.0%', '0.89', '0.75', '321.5']])
    w.nl()
    w.caption('Table 7. Held-out FMD ANOVA across clusters.')
    w.table_placeholder(
        ['Method', 'F statistic', 'p-value', 'Groups'],
        [['DBSCAN', '3.65', '0.056', '2'], ['KMeans', '8.63', '0.003', '2']])

    w.heading('DBSCAN Results', 3)
    if img('figure_07_dbscan_pca_scatter.png'):
        w.image_placeholder(img('figure_07_dbscan_pca_scatter.png'), 380)
    w.caption('Figure 7. DBSCAN clusters on PCA components. One dominant cluster absorbs most counties, with 61 noise points and a 5-county micro-cluster.')
    w.nl()
    w.caption('Table 8. DBSCAN cluster profiles.')
    w.table_placeholder(
        ['Cluster', 'Counties', 'Avg FMD', 'Median AQI', 'Uninsured', 'Bachelor+'],
        [['\u22121 (noise)', '61', '17.06', '48.8', '9.6%', '34.5%'],
         ['0 (main)', '2,746', '18.61', '41.4', '9.5%', '24.0%'],
         ['1 (small)', '5', '16.94', '56.2', '10.0%', '39.0%']])
    w.nl()
    if img('figure_08_dbscan_cluster_profile.png'):
        w.image_placeholder(img('figure_08_dbscan_cluster_profile.png'), 420)
    w.caption('Figure 8. DBSCAN cluster profiles. Noise cluster shows elevated AQI and higher education; cluster 1 has lower FMD.')

    w.heading('K-Means Results', 3)
    if img('figure_09_kmeans_pca_scatter.png'):
        w.image_placeholder(img('figure_09_kmeans_pca_scatter.png'), 380)
    w.caption('Figure 9. K-Means (k=2) on PCA embedding. Dominant cluster contains 2,785 of 2,812 counties.')
    w.nl()
    if img('figure_10_kmeans_cluster_profile.png'):
        w.image_placeholder(img('figure_10_kmeans_cluster_profile.png'), 420)
    w.caption('Figure 10. K-Means cluster profiles. Cluster 0 (27 counties) has extreme max AQI and lower FMD (ANOVA F=8.63, p=0.003).')

    w.heading('Unsupervised Sensitivity Analysis', 3)
    if img('figure_11_unsupervised_parameter_search.png'):
        w.image_placeholder(img('figure_11_unsupervised_parameter_search.png'), 420)
    w.caption('Figure 11. DBSCAN and K-Means unsupervised sensitivity search across 75 total settings: 70 DBSCAN eps/min_samples configurations and 5 K-Means k values. Selected DBSCAN eps=1.43 and min_samples=5 balances silhouette (0.76) against minimal noise (2.2%); K-Means selected k=2.')
    w.nl()
    w.para('For K-Means, silhouette dropped sharply from k=2 (0.89) to k=3 (0.70) and k=4 (0.14), indicating the data support at most two broad groups. These results should be treated as exploratory.')

    # Discussion
    w.heading('Discussion', 1)
    w.para('The enriched feature set contains some predictive signal, but not enough for confident next-year FMD forecasting. The best model improved over the Dummy baseline and approached zero R\u00b2, but large residuals remained in high-distress counties.')
    w.para('What surprised us most was that adding daily AQI features did not meaningfully improve prediction. The ablation showed that removing all 25 daily AQI variables actually decreased RMSE by 0.004. In contrast, removing education/health-access variables increased RMSE the most (+0.08), indicating socioeconomic context was more predictive than direct pollution measures.')
    w.para('The primary challenge was the tension between temporal integrity and sample size. Our leakage-safe design reduces the effective training window to 4 year-pairs. DBSCAN found a dominant county group plus outliers, while K-Means produced two clusters with stronger silhouette but similar imbalance.')
    w.para('The project\u2019s empirical result is a negative finding: annual county-level variables did not provide strong next-year FMD prediction under a leakage-safe temporal holdout. A rigorous negative finding remains scientifically valuable.')
    w.para('With more time and resources, we would: (1) rebuild the outcome from raw BRFSS microdata, (2) incorporate monthly exposure windows, (3) add healthcare provider density, RUCC rurality codes, and disability prevalence, and (4) explore spatial regression models.')

    # Ethical Considerations
    w.heading('Ethical Considerations and Notes of Caution', 1)
    w.bullet('Predictions are county-level planning signals, not individual diagnoses.')
    w.bullet('High-FMD counties should not be stigmatized; maps should guide support, not blame.')
    w.bullet('Sparse monitor coverage and imputed values carry uncertainty.')
    w.bullet('Forecasting tools should be paired with local expertise and community input.')
    w.bullet('This should not serve as causal evidence for regulatory decisions.')
    w.nl()
    w.para('Unsupervised clustering carries its own ethical risks. Assigning counties to clusters risks reinforcing stereotypes about "types" of communities. Cluster labels can be misinterpreted as fixed identities rather than statistical summaries. Our DBSCAN noise label could stigmatize 61 counties as "outliers." Because clustering excluded FMD and reintroduced it post-hoc, users may incorrectly infer causality. We emphasize these are observational associations, not causal claims.')
    w.nl()
    w.caption('Table 9. Limitations and recommended next steps.')
    w.table_placeholder(
        ['Limitation', 'Implication', 'Next Step'],
        [['Annual county aggregation', 'Smooths short-term events', 'Use monthly/daily windows'],
         ['Sparse EPA daily AQI', 'Only monitored counties', 'Add satellite estimates'],
         ['Negative income sentinels', 'Requires cleaning', 'Treat as missing, rerun'],
         ['Missing healthcare/rurality', 'Unexplained residuals', 'Add provider density, RUCC'],
         ['No causal identification', 'Not causal evidence', 'Quasi-experimental designs']])

    # Statement of Work
    w.heading('Statement of Work', 1)
    w.caption('Table 10. Statement of work.')
    w.table_placeholder(
        ['Team Member', 'Primary Contributions'],
        [['Jaeah Kim', 'Unsupervised learning analysis, clustering design, interpretation.'],
         ['Kyle Rodriguez', 'Supervised/unsupervised evaluation, repo cleanup, data gathering.'],
         ['Sophia Boettcher', 'Dataset integration, imputation workflow, report drafting.'],
         ['All members', 'EDA, data cleaning, modeling review, presentation synthesis.']])

    # Appendix A
    w.heading('Appendix A \u2014 Bibliography', 1)
    for r in [
        'Centers for Disease Control and Prevention. (n.d.). PLACES: Local Data for Better Health. https://www.cdc.gov/places',
        'Lei, K., Yang, J., & Ke, X. (2025). The impact of neighborhood environment on mental health. Frontiers in Public Health, 12, 1452744.',
        'Park, H., et al. (2024). Particulate matters and the risk of depression: KLoSA, 2016\u20132020. Environmental Health, 23(1), Article 4.',
        'U.S. Census Bureau. (2009\u20132024). American Community Survey 5-Year Estimates. https://api.census.gov/data',
        'U.S. EPA. (2026). AirData. https://aqs.epa.gov/aqsweb/airdata/download_files.html',
        'Werder, E., et al. (2024). Residential air pollution, greenspace, and mental health. Sci. Total Environ., 946, 174434.',
    ]:
        w.para(r)

    # Appendix B
    w.heading('Appendix B \u2014 Full Table of Features', 1)
    w.caption('Table 11. Full feature table.')
    w.table_placeholder(
        ['Family', 'Variables', 'Type', 'Source'],
        [['Geographic IDs', 'geoid, county_name, state_name, year', 'Int/Cat', 'Census'],
         ['Mental health', 'mental_health_prevalence (FMD)', 'Float', 'CDC PLACES'],
         ['Air quality', 'median_aqi, max_aqi, days_pm25, etc.', 'Float', 'EPA'],
         ['Engineered AQ', 'bad_air_day_ratio, good_air_day_ratio', 'Float', 'Engineered'],
         ['Climate', 'Annual temp, precip, anomalies', 'Float', 'NOAA'],
         ['Socioeconomic', 'median_income, poverty_rate, etc.', 'Float', 'ACS'],
         ['Education/health', 'Bachelor\u2019s attainment, uninsured rate', 'Float', 'ACS'],
         ['Industry', 'Manufacturing, agriculture shares', 'Float', 'ACS']])

    return w


def main():
    with open(DOC_INFO) as f:
        doc_id = json.load(f)['doc_id']
    with open(IMAGE_IDS) as f:
        images = json.load(f)

    docs = get_services()

    # 1) Clear
    print('Clearing document...')
    clear_doc(docs, doc_id)
    print('  Done.')

    # 2) Build content
    print('Building content...')
    w = build_content(images)

    # 3) Insert all text + formatting
    print('Inserting text and formatting...')
    text_reqs = w.build_text_requests()
    BATCH = 400
    for i in range(0, len(text_reqs), BATCH):
        docs.documents().batchUpdate(documentId=doc_id,
                                     body={'requests': text_reqs[i:i+BATCH]}).execute()
        print(f'  Text batch {i//BATCH+1}: {min(i+BATCH, len(text_reqs))}/{len(text_reqs)}')
        time.sleep(0.5)

    # 4) Replace image placeholders with actual images
    print('Inserting images...')
    for marker, uri, width in reversed(w.images):  # reverse to not shift earlier indices
        # Find the marker in the doc
        doc = docs.documents().get(documentId=doc_id).execute()
        full_text = ''
        for elem in doc['body']['content']:
            if 'paragraph' in elem:
                for el in elem['paragraph']['elements']:
                    if 'textRun' in el:
                        full_text += el['textRun']['content']
                    else:
                        full_text += '\x00'  # placeholder for non-text (shouldn't be here yet)
            elif 'table' in elem:
                full_text += '\x00'  # skip tables
        pos = full_text.find(marker)
        if pos < 0:
            print(f'  Warning: marker {marker} not found, skipping image')
            continue
        doc_idx = pos + 1  # +1 because doc body starts at index 1
        marker_end = doc_idx + len(marker) + 1  # +1 for the \n after marker
        reqs = [
            # Delete the marker text + newline
            {'deleteContentRange': {'range': {'startIndex': doc_idx, 'endIndex': marker_end}}},
            # Insert image at same position
            {'insertInlineImage': {
                'location': {'index': doc_idx},
                'uri': uri,
                'objectSize': {'width': {'magnitude': width, 'unit': 'PT'}},
            }},
        ]
        try:
            docs.documents().batchUpdate(documentId=doc_id, body={'requests': reqs}).execute()
            print(f'  Inserted image for {marker}')
        except Exception as e:
            print(f'  Warning: image insert failed for {marker}: {e}')
        time.sleep(0.3)

    # 5) Replace table placeholders with real tables
    print('Inserting tables...')
    for marker, headers, rows in reversed(w.table_markers):
        doc = docs.documents().get(documentId=doc_id).execute()
        # Find marker position by scanning structured elements
        marker_start = None
        marker_end = None
        running_idx = 0
        for elem in doc['body']['content']:
            if 'paragraph' in elem:
                para_text = ''
                for el in elem['paragraph']['elements']:
                    if 'textRun' in el:
                        para_text += el['textRun']['content']
                if marker in para_text:
                    marker_start = elem['startIndex']
                    marker_end = elem['endIndex']
                    break

        if marker_start is None:
            print(f'  Warning: marker {marker} not found, skipping table')
            continue

        R = 1 + len(rows)
        C = len(headers)

        # Delete marker line, insert table, fill cells
        reqs = [{'deleteContentRange': {'range': {'startIndex': marker_start, 'endIndex': marker_end}}}]
        reqs.append({'insertTable': {
            'rows': R, 'columns': C,
            'location': {'index': marker_start},
        }})
        docs.documents().batchUpdate(documentId=doc_id, body={'requests': reqs}).execute()

        # Now read the doc again to find the actual cell indices
        doc = docs.documents().get(documentId=doc_id).execute()
        # Find the table that starts near marker_start
        table_elem = None
        for elem in doc['body']['content']:
            if 'table' in elem and abs(elem['startIndex'] - marker_start) < 5:
                table_elem = elem
                break

        if table_elem is None:
            print(f'  Warning: table not found after insert for {marker}')
            continue

        # Fill cells in reverse order
        all_rows = [headers] + rows
        cell_reqs = []
        for r_idx, row_data in enumerate(reversed(all_rows)):
            actual_r = R - 1 - r_idx
            row_elem = table_elem['table']['tableRows'][actual_r]
            for c_idx, cell_text in enumerate(reversed(row_data)):
                actual_c = C - 1 - c_idx
                if actual_c >= len(row_elem['tableCells']):
                    continue
                cell = row_elem['tableCells'][actual_c]
                # Find the paragraph start in this cell
                cell_para = cell['content'][0]
                ins_idx = cell_para['startIndex']
                cell_text = str(cell_text)
                if cell_text:
                    cell_reqs.append({'insertText': {
                        'location': {'index': ins_idx},
                        'text': cell_text,
                    }})
                    cell_reqs.append(style_req(
                        ins_idx, ins_idx + len(cell_text),
                        bold=(actual_r == 0), size=9))

        if cell_reqs:
            docs.documents().batchUpdate(documentId=doc_id, body={'requests': cell_reqs}).execute()
        print(f'  Inserted table for {marker}')
        time.sleep(0.3)

    print(f'\n\u2705 Done! https://docs.google.com/document/d/{doc_id}/edit')


if __name__ == '__main__':
    main()
