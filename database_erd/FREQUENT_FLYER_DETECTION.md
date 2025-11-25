# Frequent Flyer Detection - Repeat Applicant Identification

**Generated:** 2025-11-25
**Database:** fraud_postgresql (Production)
**Tables Documented:** 2 advanced fraud detection tables

---

## Overview

The Frequent Flyer Detection system identifies applicants who repeatedly apply for properties, potentially using slight variations in their personal information to avoid detection. This helps property managers identify "professional renters" who may have been rejected elsewhere or have a history of issues.

**Key Functions:**
- **Identity Normalization** - Store canonical forms of names, emails, phone numbers
- **Fuzzy Matching** - Match current applicants against historical variations
- **Confidence Scoring** - Calculate match probability based on matched fields
- **Alert Generation** - Flag high-confidence matches for review
- **Pattern Detection** - Identify applicants applying to multiple properties

**Business Value:**
- Catch applicants rejected at other properties
- Identify professional fraud schemes
- Protect property managers from serial problem tenants
- Reduce fraud losses across property portfolio

---

## Table Inventory

### Frequent Flyer Detection (2 tables)
- **frequent_flyer_variations** - Normalized identity variations for matching
- **frequent_flyer_matched_confidences** - Match results with confidence scores

---

## Frequent Flyer Detection Architecture

```
New Applicant Submission → Extract Identity Data (name, email, phone)
                                      ↓
                         Normalize Data (lowercase, remove punctuation, etc.)
                                      ↓
                    Query frequent_flyer_variations for fuzzy matches
                                      ↓
                    For each potential match, calculate confidence score
                                      ↓
             frequent_flyer_matched_confidences (store match with score)
                                      ↓
                    If confidence > threshold → Flag for review
```

---

## Detailed Table Documentation

## 1. FREQUENT_FLYER_VARIATIONS

**Purpose:** Stores normalized identity variations for efficient fuzzy matching. Each record represents a unique combination of identity attributes seen in the system.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key (auto-generated) |
| first_name | varchar(255) | NO | Original first name |
| last_name | varchar(255) | NO | Original last name |
| email | varchar(255) | NO | Original email address |
| phone | varchar(255) | NO | Original phone number |
| normalized_first_name | varchar(255) | NO | Normalized first name (lowercase, trimmed) |
| normalized_last_name | varchar(255) | NO | Normalized last name (lowercase, trimmed) |
| normalized_email | varchar(255) | NO | Normalized email (lowercase, no dots/plus) |
| normalized_phone | varchar(255) | NO | Normalized phone (digits only) |
| inserted_at | timestamp | NO | Variation first seen |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Has many:** frequent_flyer_matched_confidences (via frequent_flyer_variation_id)
- **Implicitly links to:** applicants (via name/email/phone matching)

### Business Logic

**Normalization Rules:**

**First Name / Last Name:**
- Convert to lowercase
- Trim whitespace
- Remove special characters
- Handle common variations:
  - "Robert" vs "Bob" vs "Bobby"
  - "Michael" vs "Mike" vs "Mikey"
  - "Elizabeth" vs "Beth" vs "Liz"
  - Possibly use phonetic matching (Soundex, Metaphone)

**Email:**
- Convert to lowercase
- Remove dots (Gmail ignores dots: john.doe@gmail.com = johndoe@gmail.com)
- Remove plus addressing (john+test@gmail.com → john@gmail.com)
- Extract domain for matching

**Phone:**
- Remove all non-digits (dashes, spaces, parentheses)
- Normalize international codes
- Example: "(555) 123-4567" → "5551234567"

**Data Population:**
```
When applicant created:
1. Extract: first_name, last_name, email, phone from applicants table
2. Normalize each field using rules above
3. Check if variation already exists:
   - If yes: Reuse existing variation_id
   - If no: Create new frequent_flyer_variations record
4. Store variation_id reference (likely in applicant or applicant_details)
```

**Variation Examples:**

| Original | Normalized |
|----------|------------|
| First: "JOHN", "John", "john" | All → "john" |
| Last: "O'Brien", "OBrien", "o brien" | Varies by rules |
| Email: "John.Doe+test@Gmail.Com" | "johndoe@gmail.com" |
| Phone: "(555) 123-4567", "555-123-4567", "5551234567" | All → "5551234567" |

**Why Store Both Original and Normalized:**
- Original: Display to users (proper capitalization)
- Normalized: Matching algorithm (case-insensitive, format-agnostic)

**Unique Identity Combinations:**
Each row represents a unique combination seen:
```
Variation 1: John Smith, john@email.com, 5551234567
Variation 2: John Smith, john@email.com, 5559876543  (same person, different phone)
Variation 3: John Smith, jsmith@email.com, 5551234567  (same person, different email)
```

**Query Patterns:**

**Find all variations for a person:**
```sql
SELECT *
FROM frequent_flyer_variations
WHERE normalized_first_name = 'john'
  AND normalized_last_name = 'smith';
```

**Find variations by email:**
```sql
SELECT *
FROM frequent_flyer_variations
WHERE normalized_email = 'johndoe@gmail.com';
```

**Find variations by phone:**
```sql
SELECT *
FROM frequent_flyer_variations
WHERE normalized_phone = '5551234567';
```

---

## 2. FREQUENT_FLYER_MATCHED_CONFIDENCES

**Purpose:** Stores match results when a new applicant submission is compared against historical variations. Records which fields matched and overall confidence score.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key (auto-generated) |
| applicant_submission_id | uuid | NO | **FK → applicant_submissions.id** (current submission) |
| frequent_flyer_variation_id | uuid | NO | **FK → frequent_flyer_variations.id** (matched variation) |
| first_name_matched | boolean | NO | First name matches |
| last_name_matched | boolean | NO | Last name matches |
| email_matched | boolean | NO | Email matches |
| phone_matched | boolean | NO | Phone number matches |
| confidence_score | integer | NO | Overall match confidence (0-100) |
| inserted_at | timestamp | NO | Match timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** applicant_submissions (via applicant_submission_id)
- **Belongs to:** frequent_flyer_variations (via frequent_flyer_variation_id)

### Business Logic

**Matching Algorithm (Conceptual):**

**Step 1: Extract current applicant data**
```
current_applicant = {
  first_name: "John",
  last_name: "Smith",
  email: "j.smith@gmail.com",
  phone: "(555) 123-4567"
}
```

**Step 2: Normalize current data**
```
normalized = {
  first_name: "john",
  last_name: "smith",
  email: "jsmith@gmail.com",
  phone: "5551234567"
}
```

**Step 3: Query for potential matches**
```sql
SELECT *
FROM frequent_flyer_variations
WHERE
  normalized_first_name = 'john' OR
  normalized_last_name = 'smith' OR
  normalized_email = 'jsmith@gmail.com' OR
  normalized_phone = '5551234567';
```

**Step 4: Calculate confidence score for each match**
```
Match Result:
- first_name_matched: TRUE (john = john)
- last_name_matched: TRUE (smith = smith)
- email_matched: TRUE (jsmith@gmail.com = jsmith@gmail.com)
- phone_matched: FALSE (5551234567 ≠ 5559876543)

Confidence Calculation:
- First name match: +25 points
- Last name match: +25 points
- Email match: +30 points
- Phone match: +20 points (if matched)
Total: 80 points (high confidence match)
```

**Confidence Score Thresholds:**
- **90-100:** Very high confidence - Almost certainly same person
- **70-89:** High confidence - Likely same person, review recommended
- **50-69:** Medium confidence - Possible match, investigate further
- **30-49:** Low confidence - Weak match, may be coincidence
- **0-29:** Very low confidence - Unlikely to be same person

**Alert Thresholds:**
- **Automatic flag:** confidence_score >= 80
- **Manual review:** confidence_score >= 50
- **Informational only:** confidence_score < 50

**Match Patterns:**

**Pattern 1: Same person, all fields match (100 points)**
```
first_name_matched: TRUE
last_name_matched: TRUE
email_matched: TRUE
phone_matched: TRUE
confidence_score: 100
→ Almost certainly same person
```

**Pattern 2: Same person, new phone number (80 points)**
```
first_name_matched: TRUE
last_name_matched: TRUE
email_matched: TRUE
phone_matched: FALSE
confidence_score: 80
→ Likely same person with new phone
```

**Pattern 3: Same person, new email (70 points)**
```
first_name_matched: TRUE
last_name_matched: TRUE
email_matched: FALSE
phone_matched: TRUE
confidence_score: 70
→ Likely same person with new email
```

**Pattern 4: Partial match, common name (50 points)**
```
first_name_matched: TRUE
last_name_matched: TRUE
email_matched: FALSE
phone_matched: FALSE
confidence_score: 50
→ Could be different person with same name
```

**Pattern 5: Email/phone match only (50-60 points)**
```
first_name_matched: FALSE
last_name_matched: FALSE
email_matched: TRUE
phone_matched: TRUE
confidence_score: 50
→ Suspicious - using different name with same contact info
→ HIGH PRIORITY for fraud investigation!
```

**Query Patterns:**

**High confidence matches for submission:**
```sql
SELECT
    ffmc.*,
    ffv.first_name,
    ffv.last_name,
    ffv.email,
    ffv.phone
FROM frequent_flyer_matched_confidences ffmc
JOIN frequent_flyer_variations ffv ON ffmc.frequent_flyer_variation_id = ffv.id
WHERE ffmc.applicant_submission_id = :submission_id
  AND ffmc.confidence_score >= 70
ORDER BY ffmc.confidence_score DESC;
```

**Applicants with most frequent flyer matches:**
```sql
SELECT
    asub.id,
    a.full_name,
    a.email,
    COUNT(ffmc.id) as match_count,
    MAX(ffmc.confidence_score) as highest_confidence
FROM applicant_submissions asub
JOIN applicants a ON asub.applicant_id = a.id
JOIN frequent_flyer_matched_confidences ffmc ON ffmc.applicant_submission_id = asub.id
WHERE asub.inserted_at > NOW() - interval '30 days'
GROUP BY asub.id, a.full_name, a.email
HAVING COUNT(ffmc.id) > 3
ORDER BY match_count DESC;
```

---

## Integration with Screening Workflow

### Data Flow

**1. New Applicant Submission:**
```
1. Applicant created in applicants table
2. applicant_submissions record created
3. Extract identity data (name, email, phone)
4. Normalize data
5. Query frequent_flyer_variations for matches
6. For each match above threshold:
   - Calculate confidence score
   - Create frequent_flyer_matched_confidences record
7. If any match has confidence >= 80:
   - Flag entry for review
   - Add note to entry_log
   - Potentially trigger webhook alert
```

**2. Reviewer Workflow:**
```
1. Reviewer opens entry marked "Frequent Flyer Alert"
2. UI shows:
   - Current applicant info
   - Matched variations with confidence scores
   - Previous submission history
   - Previous results (approved/rejected)
3. Reviewer investigates:
   - Same person applying multiple times?
   - Why were they rejected before?
   - Are they providing fraudulent documents?
4. Reviewer makes decision:
   - Approve if previous issues resolved
   - Reject if pattern of fraud
   - Escalate if unclear
```

### Complete Context Query

```sql
-- Get full frequent flyer context for an applicant
SELECT
    -- Current Applicant
    a.full_name as current_name,
    a.email as current_email,
    a.phone as current_phone,
    asub.id as current_submission_id,

    -- Matched Variation
    ffv.first_name as matched_first_name,
    ffv.last_name as matched_last_name,
    ffv.email as matched_email,
    ffv.phone as matched_phone,

    -- Match Details
    ffmc.first_name_matched,
    ffmc.last_name_matched,
    ffmc.email_matched,
    ffmc.phone_matched,
    ffmc.confidence_score,

    -- Current Entry
    e.short_id as entry_id,
    e.result as current_result,
    e.status as current_status,
    p.name as property_name

FROM applicant_submissions asub
JOIN applicants a ON asub.applicant_id = a.id
JOIN entries e ON a.entry_id = e.id
JOIN folders f ON e.folder_id = f.id
JOIN properties p ON f.property_id = p.id
JOIN frequent_flyer_matched_confidences ffmc ON ffmc.applicant_submission_id = asub.id
JOIN frequent_flyer_variations ffv ON ffmc.frequent_flyer_variation_id = ffv.id
WHERE asub.id = :submission_id
ORDER BY ffmc.confidence_score DESC;
```

---

## Performance Considerations

### Indexes Recommended

```sql
-- frequent_flyer_variations: Normalized field lookups
CREATE INDEX idx_ffv_normalized_first_name
  ON frequent_flyer_variations(normalized_first_name);

CREATE INDEX idx_ffv_normalized_last_name
  ON frequent_flyer_variations(normalized_last_name);

CREATE INDEX idx_ffv_normalized_email
  ON frequent_flyer_variations(normalized_email);

CREATE INDEX idx_ffv_normalized_phone
  ON frequent_flyer_variations(normalized_phone);

-- frequent_flyer_variations: Composite index for multi-field matching
CREATE INDEX idx_ffv_name_email_phone
  ON frequent_flyer_variations(normalized_first_name, normalized_last_name, normalized_email, normalized_phone);

-- frequent_flyer_matched_confidences: Lookup by submission
CREATE INDEX idx_ffmc_submission
  ON frequent_flyer_matched_confidences(applicant_submission_id);

-- frequent_flyer_matched_confidences: Lookup by variation
CREATE INDEX idx_ffmc_variation
  ON frequent_flyer_matched_confidences(frequent_flyer_variation_id);

-- frequent_flyer_matched_confidences: High confidence matches
CREATE INDEX idx_ffmc_high_confidence
  ON frequent_flyer_matched_confidences(confidence_score DESC)
  WHERE confidence_score >= 70;

-- frequent_flyer_matched_confidences: Match pattern analysis
CREATE INDEX idx_ffmc_match_pattern
  ON frequent_flyer_matched_confidences(first_name_matched, last_name_matched, email_matched, phone_matched);
```

### Query Optimization

**Matching query should use indexes:**
```sql
-- This query should use idx_ffv_normalized_email
SELECT * FROM frequent_flyer_variations
WHERE normalized_email = 'johndoe@gmail.com';

-- This query should use idx_ffmc_submission
SELECT * FROM frequent_flyer_matched_confidences
WHERE applicant_submission_id = :submission_id;
```

**Batch processing for high volume:**
- Run matching algorithm asynchronously
- Queue new submissions for processing
- Process in batches during off-peak hours

---

## Business Metrics & KPIs

### Frequent Flyer Detection Rate

```sql
-- Percentage of submissions with frequent flyer matches
SELECT
    COUNT(DISTINCT asub.id) as total_submissions,
    COUNT(DISTINCT ffmc.applicant_submission_id) as submissions_with_matches,
    COUNT(DISTINCT ffmc.applicant_submission_id) * 100.0 / COUNT(DISTINCT asub.id) as match_rate
FROM applicant_submissions asub
LEFT JOIN frequent_flyer_matched_confidences ffmc
    ON ffmc.applicant_submission_id = asub.id
    AND ffmc.confidence_score >= 70
WHERE asub.inserted_at > NOW() - interval '30 days';
```

### Confidence Score Distribution

```sql
-- Distribution of confidence scores
SELECT
    CASE
        WHEN confidence_score >= 90 THEN '90-100 (Very High)'
        WHEN confidence_score >= 70 THEN '70-89 (High)'
        WHEN confidence_score >= 50 THEN '50-69 (Medium)'
        WHEN confidence_score >= 30 THEN '30-49 (Low)'
        ELSE '0-29 (Very Low)'
    END as confidence_bucket,
    COUNT(*) as match_count
FROM frequent_flyer_matched_confidences
WHERE inserted_at > NOW() - interval '30 days'
GROUP BY confidence_bucket
ORDER BY
    CASE confidence_bucket
        WHEN '90-100 (Very High)' THEN 1
        WHEN '70-89 (High)' THEN 2
        WHEN '50-69 (Medium)' THEN 3
        WHEN '30-49 (Low)' THEN 4
        ELSE 5
    END;
```

### Match Pattern Analysis

```sql
-- Most common match patterns
SELECT
    first_name_matched,
    last_name_matched,
    email_matched,
    phone_matched,
    COUNT(*) as occurrences,
    AVG(confidence_score) as avg_confidence
FROM frequent_flyer_matched_confidences
WHERE inserted_at > NOW() - interval '30 days'
GROUP BY first_name_matched, last_name_matched, email_matched, phone_matched
ORDER BY occurrences DESC;
```

### Serial Applicants

```sql
-- Applicants who match 5+ variations (potential professional applicants)
SELECT
    a.full_name,
    a.email,
    COUNT(DISTINCT ffmc.id) as match_count,
    MAX(ffmc.confidence_score) as highest_confidence,
    COUNT(DISTINCT p.id) as properties_applied_to
FROM applicants a
JOIN applicant_submissions asub ON asub.applicant_id = a.id
JOIN frequent_flyer_matched_confidences ffmc ON ffmc.applicant_submission_id = asub.id
JOIN entries e ON a.entry_id = e.id
JOIN folders f ON e.folder_id = f.id
JOIN properties p ON f.property_id = p.id
WHERE asub.inserted_at > NOW() - interval '90 days'
GROUP BY a.id, a.full_name, a.email
HAVING COUNT(DISTINCT ffmc.id) >= 5
ORDER BY match_count DESC;
```

---

## Use Cases & Scenarios

### Use Case 1: Serial Fraud Applicant
**Scenario:** Applicant submits fraudulent documents at Property A, gets rejected. Re-applies at Property B with slightly different info.

**Detection:**
```
Property A Application:
- Name: John Smith
- Email: jsmith@gmail.com
- Phone: 555-123-4567
- Result: FRAUD (forged paystub)

Property B Application:
- Name: John Smith
- Email: johnsmith@gmail.com (different email)
- Phone: 555-123-4567 (same phone)

Frequent Flyer Match:
- confidence_score: 70
- first_name_matched: TRUE
- last_name_matched: TRUE
- email_matched: FALSE
- phone_matched: TRUE

Action: Flag for review, reviewer sees previous FRAUD result
```

### Use Case 2: Legitimate Re-application
**Scenario:** Applicant rejected for insufficient income, gets a better job, re-applies 6 months later.

**Detection:**
```
First Application:
- Name: Jane Doe
- Email: jane.doe@email.com
- Phone: 555-999-8888
- Result: REJECTED (insufficient income)

Second Application:
- Name: Jane Doe
- Email: jane.doe@email.com
- Phone: 555-999-8888 (all same)

Frequent Flyer Match:
- confidence_score: 100
- All fields matched

Action: Flag for review, reviewer sees previous rejection was income-based,
        reviews new income documents, approves if now sufficient
```

### Use Case 3: Identity Theft Detection
**Scenario:** Fraudster uses stolen identity info but with their own contact details.

**Detection:**
```
Legitimate Application:
- Name: Alice Johnson
- Email: alice@legitemail.com
- Phone: 555-111-2222

Fraudulent Application:
- Name: Alice Johnson (stolen name)
- Email: fraud@fakeemail.com (fraudster's email)
- Phone: 555-999-9999 (fraudster's phone)

Frequent Flyer Match:
- confidence_score: 50
- first_name_matched: TRUE
- last_name_matched: TRUE
- email_matched: FALSE
- phone_matched: FALSE

Action: Flag for review - suspicious pattern (name match but different contacts)
```

---

## Summary

**2 Tables Documented:**
- **frequent_flyer_variations** - Normalized identity storage (11 columns)
- **frequent_flyer_matched_confidences** - Match results with scoring (10 columns)

**Key Features:**
- Identity normalization for fuzzy matching
- Confidence scoring based on field matches
- Boolean flags for each matched field
- Historical variation tracking

**Business Value:**
- Detect repeat applicants across properties
- Identify professional fraud schemes
- Protect against serial problem tenants
- Reduce fraud losses portfolio-wide

**Integration Points:**
- applicant_submissions (current application being screened)
- applicants (identity data extraction)
- entries (flagging for review)
- entry_log (audit trail of frequent flyer alerts)

**Performance:**
- Indexed normalized fields for fast matching
- Batch processing for high volume
- Confidence thresholds for alert prioritization

---

**Related Documentation:**
- [CORE_ENTITY_MODEL.md](CORE_ENTITY_MODEL.md) - applicants, applicant_submissions
- [FRAUD_DETECTION_WORKFLOW.md](FRAUD_DETECTION_WORKFLOW.md) - fraud result integration
- [REVIEW_QUEUE_SYSTEM.md](REVIEW_QUEUE_SYSTEM.md) - review flagging and escalation

---

**Generated:** 2025-11-25
**Last Updated:** 2025-11-25
**Version:** 1.0
**Tables Documented:** 2 of 75 core tables
