## 2. Requirements

### 2.1 Functional Requirements

#### FR-01: Data Loading and Validation

**Priority:** High

**Description:**

The system shall read data from the frozen snapshot of the dataset to ensure consistency. The data is read only to preserve the raw data. The data must be verified for data integrity and preserve the original columns and thus generate an analysis-ready dataset.

**Acceptance Criteria:**

- **AC-1:** The system shall read rental records from the frozen SQLite database in read only mode and preserve identifier "id".
- **AC-2:** The system shall detect missing or duplicate listing IDs without quietly removing them.
- **AC-3:** The system shall identify records that have missing values yet determine whether these incomplete data are still eligible for analysis. For example, missing area footage does not prevent the house to be analyzed location wise.

**Related Tests:** To be mapped to the corresponding data validation tests.

#### FR-02: Rental Listing Filtering

**Priority:** High

**Description:**

The system shall allow users to filter rental listings by maximum monthly rent, bedroom count, and maximum straight-line distance from UCSD. Al the 3 parameters shall be optional, with 0 parameters being the least accurate, to 3 parameters being the most.

**Acceptance Criteria:**

- **AC-1:** The system should only return results that matches the specified options, unspecified options should not bound the filtering process.
- **AC-2:** The system should use inclusive on rent but exact numbers on bedrooms. While the distance can be neglected. If so, the plot would show all possible houses within the 10-mile radius, as in the whole dataset.
- **AC-3:** The system should throw exact error when the inputs are invalid, such as string input or negative input.

**Related Tests:** FT-02 (proposed).

#### FR-03: Rental Price Analysis and Visualization

**Priority:** High

**Description:**

The system shall create statistics for rental prices group by bedroom counts and create respective visualizations. It should also indicate missing values and whether the function put it into calculation. Statistics include n, mean, median, q1, q3, min, max.

**Acceptance Criteria:**

- **AC-1:** The system shall calculate the sample count, mean, median, quartiles, minimum, and maximum monthly rent for each bedroom-count group.
- **AC-2:** The system shall generate statistical plots of different bedroom counts, with clear labels, units, and sample sizes.
- **AC-3:** The system shall include eligible records with missing floor area in monthly rent statistics but exclude them from rent-per-square-foot calculations. The system shall report the number of valid and excluded records for each relevant calculation.

**Related Tests:** UT-A3 and FT-01 (proposed).

---

### 2.2 Non-Functional Requirements

#### NFR-01: Reproducibility

**Priority:** High

**Description:**

The system shall produce consistent outputs, and for every user who , and for every user who uses this function, it should produce consistent results. The function does not require further API requests.

**Acceptance Criteria:**

- **AC-1:** With same input parameters, multiple users should produce the same results.
- **AC-2:** The system shall use the frozen dataset and documented processing rules to ensure that the analysis can be reproduced without retrieving new rental data.

**Related Tests:** Repeated execution and comparison of analysis results (planned).

#### NFR-02: Data Integrity

**Priority:** High

**Description:**

The system shall preserve the integrity of the original rental dataset throughout data processing and analysis. Processed data and analysis results shall be stored separately from the frozen dataset.

**Acceptance Criteria:**

- **AC-1:** The original frozen data files shall remain unchanged after data processing and analysis, as verified by matching SHA-256 checksums before and after execution.
- **AC-2:** The system shall store processed datasets and generated analysis results in separate directories without overwriting the original frozen snapshot.

**Related Tests:** Snapshot checksum verification and output-directory inspection.

#### NFR-03: Reliability and Error Handling

**Priority:** Medium

**Description:**

The system shall handle invalid inputs and data access failures in a predictable manner. Errors shall be clearly reported without silently producing invalid analysis results.

**Acceptance Criteria:**

- **AC-1:** Invalid filtering parameters, such as negative rental budgets, negative distances, or non-integer bedroom counts, shall produce clear error messages.
- **AC-2:** If the required dataset is missing, corrupted, or cannot be accessed, the system shall report the failure and stop the affected operation without modifying the frozen dataset.

**Related Tests:** Invalid-input and data-access failure tests (planned).
