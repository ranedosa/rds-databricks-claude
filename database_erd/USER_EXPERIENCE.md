# User Experience & UI Customization

**Generated:** 2025-11-25
**Database:** fraud_postgresql (Production)
**Tables Documented:** 5 tables

---

## Overview

This document covers tables that enhance user experience through in-app announcements, notifications, and customizable UI preferences. These tables enable administrators to communicate platform updates, manage feature rollouts, and allow users to personalize their dashboard experience.

**Categories:**
1. **Announcements System (3 tables):** announcement, announcement_role, announcement_user_was_shown
2. **UI Customization (2 tables):** user_role_sort_priority, user_tab_role_sort_priority

---

## Table of Contents

1. [Announcements System](#1-announcements-system-3-tables)
   - announcement
   - announcement_role
   - announcement_user_was_shown
2. [UI Customization & Preferences](#2-ui-customization--preferences-2-tables)
   - user_role_sort_priority
   - user_tab_role_sort_priority

---

## 1. Announcements System (3 Tables)

### announcement

**Purpose:** System-wide announcements for communicating platform updates, new features, maintenance windows, and important notices to users

**Primary Key:** id (bigint, auto-incrementing)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| title | varchar(255) | NO | - | Announcement headline |
| is_active | boolean | NO | false | Announcement enabled/disabled |
| description | text | YES | - | Detailed announcement content (supports markdown/HTML) |
| close_button_label | varchar(255) | YES | - | Custom close button text (e.g., "Got it", "Dismiss") |
| confirm_button_label | varchar(255) | YES | - | Custom confirm button text (e.g., "Learn More", "Try it Now") |
| redirect_to | varchar(255) | YES | - | URL for confirm button action |
| image_url | varchar(255) | YES | - | Banner image or icon URL |
| inserted_at | timestamp | NO | - | Announcement creation timestamp |
| updated_at | timestamp | NO | - | Last update timestamp |

#### Relationships

**Has many:**
- **announcement_role** - Role-based targeting
- **announcement_user_was_shown** - Display tracking per user

#### Business Logic

**Announcement Types:**

1. **Feature Announcements:**
   - title: "New Identity Verification Integration"
   - description: "We've added Persona as an alternative ID verification provider..."
   - confirm_button_label: "Learn More"
   - redirect_to: "/docs/identity-verification"
   - Image showing new feature

2. **Maintenance Notices:**
   - title: "Scheduled Maintenance - December 15th"
   - description: "Platform will be unavailable from 2am-4am EST for system upgrades"
   - close_button_label: "Acknowledge"
   - No redirect (information only)

3. **Product Updates:**
   - title: "Faster Fraud Detection with ML v2"
   - description: "Our new ML model reduces false positives by 30%"
   - confirm_button_label: "See Details"
   - redirect_to: "/blog/ml-v2-release"

4. **Action Required:**
   - title: "Update Your API Keys by Jan 1st"
   - description: "Legacy API keys will be deprecated. Please generate new keys..."
   - confirm_button_label: "Update Keys"
   - redirect_to: "/settings/api-keys"
   - Critical priority

**Display Behavior:**

**Modal/Banner Display:**
- Announcement shown as modal on login or banner at top of dashboard
- User must acknowledge (click close or confirm button)
- Dismissal tracked in announcement_user_was_shown

**Targeting:**
- No announcement_role records = show to ALL users
- With announcement_role records = show only to specified roles (admins, reviewers, etc.)

**Lifecycle:**
1. Admin creates announcement (is_active = false initially)
2. Admin configures targeting (announcement_role records)
3. Admin activates announcement (is_active = true)
4. Users see announcement on next login
5. Users dismiss/acknowledge → announcement_user_was_shown record created
6. Admin deactivates after campaign (is_active = false)

**Content Formatting:**
- description supports markdown or HTML
- image_url displays banner/icon (optional)
- Custom button labels for branding consistency

#### Query Examples

```sql
-- Active announcements for specific role
SELECT
    a.title,
    a.description,
    a.confirm_button_label,
    a.redirect_to,
    r.name as target_role
FROM announcement a
LEFT JOIN announcement_role ar ON a.id = ar.announcement_id
LEFT JOIN role r ON ar.role_id = r.id
WHERE a.is_active = true
ORDER BY a.inserted_at DESC;

-- Announcements not yet shown to user
SELECT
    a.id,
    a.title,
    a.description,
    a.close_button_label,
    a.confirm_button_label,
    a.redirect_to,
    a.image_url
FROM announcement a
LEFT JOIN announcement_user_was_shown auws
    ON a.id = auws.announcement_id
    AND auws.user_id = 'user-uuid-here'
WHERE a.is_active = true
    AND auws.id IS NULL  -- Not shown to this user
ORDER BY a.inserted_at ASC;  -- Oldest first

-- Announcement performance metrics
SELECT
    a.title,
    a.inserted_at,
    COUNT(auws.id) as users_shown,
    COUNT(DISTINCT auws.user_id) as unique_users,
    a.is_active
FROM announcement a
LEFT JOIN announcement_user_was_shown auws ON a.id = auws.announcement_id
GROUP BY a.id, a.title, a.inserted_at, a.is_active
ORDER BY a.inserted_at DESC;

-- Role-specific announcement coverage
SELECT
    r.name as role,
    COUNT(DISTINCT a.id) as active_announcements
FROM role r
LEFT JOIN announcement_role ar ON r.id = ar.role_id
LEFT JOIN announcement a ON ar.announcement_id = a.id AND a.is_active = true
GROUP BY r.name
ORDER BY active_announcements DESC;
```

#### Use Cases

**New Feature Rollout:**
```sql
-- Target reviewers only for new review UI
INSERT INTO announcement (title, description, confirm_button_label, redirect_to, is_active)
VALUES (
    'New Review Dashboard Available',
    'Try our redesigned review interface with faster document viewing and improved fraud indicators.',
    'Switch to New UI',
    '/review/beta',
    true
);

-- Target only reviewer roles
INSERT INTO announcement_role (announcement_id, role_id)
SELECT LAST_INSERT_ID(), id FROM role WHERE name IN ('reviewer', 'senior_reviewer', 'qa');
```

**Critical Security Update:**
```sql
-- Show to all admins
INSERT INTO announcement (title, description, confirm_button_label, redirect_to, is_active)
VALUES (
    'Security Update Required',
    'Please enable two-factor authentication on your account by end of week.',
    'Enable 2FA Now',
    '/settings/security',
    true
);

-- Target admins
INSERT INTO announcement_role (announcement_id, role_id)
SELECT LAST_INSERT_ID(), id FROM role WHERE name = 'admin';
```

---

### announcement_role

**Purpose:** Many-to-many junction table linking announcements to specific user roles for targeted messaging

**Primary Key:** id (bigint, auto-incrementing)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| announcement_id | bigint | NO | - | Announcement FK → announcement.id |
| role_id | bigint | NO | - | Role FK → role.id |

#### Relationships

**Belongs to:**
- **announcement** (announcement_id) - The announcement
- **role** (role_id) - The role that should see the announcement

#### Business Logic

**Targeting Logic:**

**No announcement_role records:**
- Announcement shown to ALL users regardless of role
- Global announcements (maintenance, company-wide updates)

**With announcement_role records:**
- Announcement shown ONLY to users with matching roles
- Role-specific features, permissions changes, training

**Examples:**

```sql
-- Show to reviewers only
INSERT INTO announcement_role (announcement_id, role_id)
VALUES (1, (SELECT id FROM role WHERE name = 'reviewer'));

-- Show to multiple roles
INSERT INTO announcement_role (announcement_id, role_id)
SELECT 1, id FROM role WHERE name IN ('admin', 'property_manager');
```

**Query Pattern:**
```sql
-- Get announcements for specific user
SELECT DISTINCT a.*
FROM announcement a
LEFT JOIN announcement_role ar ON a.id = ar.announcement_id
JOIN users u ON u.id = 'user-uuid'
WHERE a.is_active = true
    AND (ar.role_id IS NULL OR ar.role_id = (SELECT id FROM role WHERE name = u.role))
    AND NOT EXISTS (
        SELECT 1 FROM announcement_user_was_shown auws
        WHERE auws.announcement_id = a.id AND auws.user_id = u.id
    );
```

---

### announcement_user_was_shown

**Purpose:** Tracks which users have seen/dismissed each announcement to prevent repeated display

**Primary Key:** id (bigint, auto-incrementing)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| announcement_id | bigint | NO | - | Announcement FK → announcement.id |
| user_id | uuid | NO | - | User FK → users.id |
| inserted_at | timestamp | NO | - | When user saw/dismissed announcement |

#### Relationships

**Belongs to:**
- **announcement** (announcement_id) - The announcement shown
- **users** (user_id) - The user who saw it

#### Business Logic

**Record Creation:**
- Record created when user clicks "Close" or "Confirm" button
- Prevents announcement from showing again
- Tracks engagement timing

**Use Cases:**

1. **Dismiss Tracking:**
   - User clicks "Got it" → record created
   - Announcement never shown again to this user

2. **Confirm Tracking:**
   - User clicks "Learn More" → record created + redirect
   - Tracks who engaged with announcement

3. **Analytics:**
   - How many users saw announcement?
   - How quickly did users dismiss?
   - Who hasn't seen critical announcement?

#### Query Examples

```sql
-- Users who saw announcement
SELECT
    u.email,
    u.first_name,
    u.last_name,
    auws.inserted_at as seen_at
FROM announcement_user_was_shown auws
JOIN users u ON auws.user_id = u.id
WHERE auws.announcement_id = 1
ORDER BY auws.inserted_at DESC;

-- Users who HAVEN'T seen active announcement
SELECT
    u.email,
    u.first_name,
    u.last_name,
    u.role
FROM users u
LEFT JOIN announcement_user_was_shown auws
    ON auws.user_id = u.id
    AND auws.announcement_id = 1
WHERE auws.id IS NULL
    AND u.is_archived = false
ORDER BY u.email;

-- Announcement engagement speed
SELECT
    a.title,
    COUNT(auws.id) as total_views,
    AVG(EXTRACT(EPOCH FROM (auws.inserted_at - a.inserted_at))) / 3600 as avg_hours_to_view
FROM announcement a
LEFT JOIN announcement_user_was_shown auws ON a.id = auws.announcement_id
WHERE a.inserted_at > NOW() - interval '30 days'
GROUP BY a.id, a.title
ORDER BY total_views DESC;
```

---

## 2. UI Customization & Preferences (2 Tables)

### user_role_sort_priority

**Purpose:** Configurable sorting priorities for dashboard lists based on user role (similar to role_entry_status_sort_priority but more general)

**Primary Key:** id (bigint, auto-incrementing)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| role_id | bigint | NO | - | Role FK → role.id |
| priority | integer | NO | - | Sort order (lower = higher priority) |

#### Relationships

**Belongs to:**
- **role** (role_id) - The user role

#### Business Logic

**Purpose:**
- Different roles see different default sort orders in dashboards
- Reviewers prioritize urgent items
- Admins prioritize escalated items
- Property managers prioritize pending items

**Priority System:**
- Lower integer = Higher priority (appears first in list)
- priority = 1 → Top of list
- priority = 10 → Bottom of list

**Example Configuration:**

**Reviewers:**
- priority = 1: Entries assigned to me
- priority = 2: Entries flagged for review
- priority = 3: High-confidence fraud detections
- priority = 4: Standard review queue

**Admins:**
- priority = 1: Escalated entries
- priority = 2: Disputed entries
- priority = 3: Entries with errors
- priority = 4: Standard entries

**Property Managers:**
- priority = 1: My properties - pending approval
- priority = 2: My properties - needs review
- priority = 3: My properties - completed
- priority = 4: Other properties

#### Query Examples

```sql
-- Get sort priorities for a role
SELECT
    r.name as role_name,
    ursp.priority,
    ursp.id
FROM user_role_sort_priority ursp
JOIN role r ON ursp.role_id = r.id
WHERE r.name = 'reviewer'
ORDER BY ursp.priority ASC;

-- Compare priorities across roles
SELECT
    r.name as role_name,
    ursp.priority,
    COUNT(*) as config_count
FROM user_role_sort_priority ursp
JOIN role r ON ursp.role_id = r.id
GROUP BY r.name, ursp.priority
ORDER BY r.name, ursp.priority;
```

**Note:** This table appears to be a more general-purpose version of `role_entry_status_sort_priority` (documented in REVIEW_QUEUE_SYSTEM.md). The specific use case may depend on application logic not evident from schema alone.

---

### user_tab_role_sort_priority

**Purpose:** Configurable tab ordering in the UI based on user role and role group (dashboard tab customization)

**Primary Key:** id (bigint, auto-incrementing)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| role_id | bigint | NO | - | Role FK → role.id |
| role_group | enum | NO | - | Tab group category (enum type) |
| priority | integer | NO | - | Tab display order (lower = leftmost) |

#### Relationships

**Belongs to:**
- **role** (role_id) - The user role

#### Business Logic

**Purpose:**
- Customize dashboard tab order by role
- Show most relevant tabs first for each role type
- Hide/reorder tabs based on permissions

**role_group Enum (likely values):**
- **reviews:** Review queue tabs
- **properties:** Property management tabs
- **reports:** Reporting and analytics tabs
- **settings:** Configuration tabs
- **admin:** Administrative tabs

**Tab Ordering Examples:**

**Reviewer Dashboard:**
- priority = 1, role_group = 'reviews' → Review Queue (leftmost tab)
- priority = 2, role_group = 'reviews' → My Reviews
- priority = 3, role_group = 'reports' → Performance
- Settings tabs hidden or low priority

**Property Manager Dashboard:**
- priority = 1, role_group = 'properties' → My Properties (leftmost tab)
- priority = 2, role_group = 'reviews' → Pending Approvals
- priority = 3, role_group = 'reports' → Property Analytics
- priority = 4, role_group = 'settings' → Property Settings

**Admin Dashboard:**
- priority = 1, role_group = 'admin' → System Status (leftmost tab)
- priority = 2, role_group = 'reviews' → All Reviews
- priority = 3, role_group = 'properties' → All Properties
- priority = 4, role_group = 'reports' → Platform Analytics
- priority = 5, role_group = 'settings' → System Settings

#### Query Examples

```sql
-- Get tab ordering for a specific role
SELECT
    r.name as role_name,
    utrsp.role_group,
    utrsp.priority
FROM user_tab_role_sort_priority utrsp
JOIN role r ON utrsp.role_id = r.id
WHERE r.name = 'reviewer'
ORDER BY utrsp.priority ASC;

-- Compare tab priorities across all roles
SELECT
    r.name as role_name,
    utrsp.role_group,
    utrsp.priority
FROM user_tab_role_sort_priority utrsp
JOIN role r ON utrsp.role_id = r.id
ORDER BY r.name, utrsp.priority ASC;

-- Find roles with specific tab visible
SELECT
    r.name as role_name,
    utrsp.priority
FROM user_tab_role_sort_priority utrsp
JOIN role r ON utrsp.role_id = r.id
WHERE utrsp.role_group = 'admin'
ORDER BY utrsp.priority ASC;
```

**Implementation Pattern:**
```javascript
// Frontend fetches tab config for logged-in user
const tabs = await fetchTabs(user.role_id);

// Tabs ordered by priority
[
  { group: 'reviews', label: 'Review Queue', priority: 1 },
  { group: 'reviews', label: 'My Reviews', priority: 2 },
  { group: 'reports', label: 'Performance', priority: 3 }
]

// Render tabs in priority order (1 = leftmost)
```

---

## Performance Considerations

### Recommended Indexes

**announcement:**
- Index on is_active (filtering active announcements)
- Index on inserted_at (ordering by date)

**announcement_role:**
- Index on announcement_id (FK lookup)
- Index on role_id (FK lookup)
- Composite index (announcement_id, role_id) for targeting queries

**announcement_user_was_shown:**
- Composite index (announcement_id, user_id) for "already shown" checks
- Index on user_id (user-specific queries)
- Index on inserted_at (analytics queries)

**user_role_sort_priority:**
- Index on role_id (FK lookup)
- Index on priority (sorting)
- Composite index (role_id, priority)

**user_tab_role_sort_priority:**
- Composite index (role_id, role_group, priority) for tab ordering queries
- Index on role_id (FK lookup)

---

## Summary

### Key Features

**Announcements System:**
- Role-based targeting for relevant messaging
- Rich content support (text, images, links)
- Engagement tracking (who saw, when dismissed)
- Customizable call-to-action buttons

**UI Customization:**
- Role-specific dashboard layouts
- Configurable list sorting priorities
- Customizable tab ordering
- Personalized user experience per role

### Use Cases

**Communication:**
- Feature launches with targeted rollout
- Maintenance windows and downtime notices
- Critical security updates
- Training and onboarding materials

**User Experience:**
- Show reviewers their urgent queue first
- Show admins escalated items first
- Show property managers their properties first
- Hide irrelevant tabs for each role

### Integration Points

**With User Management:**
- announcement_user_was_shown tracks per-user engagement
- announcement_role targets specific roles
- Sort priorities and tab orders adapt to user role

**With Review Workflows:**
- Announcements for new review features
- Custom dashboard layouts for reviewer efficiency

**With Reporting:**
- Analytics on announcement engagement
- Track feature adoption post-announcement

---

## Related Documentation

- [CORE_ENTITY_MODEL.md](CORE_ENTITY_MODEL.md) - Users and roles
- [REVIEW_QUEUE_SYSTEM.md](REVIEW_QUEUE_SYSTEM.md) - role_entry_status_sort_priority (similar concept)
- [FEATURES_CONFIGURATION.md](FEATURES_CONFIGURATION.md) - Feature flags and rollout
- [README.md](README.md) - Project overview

---

**Generated:** 2025-11-25
**Database:** fraud_postgresql
**Tables Documented:** 5 (announcement, announcement_role, announcement_user_was_shown, user_role_sort_priority, user_tab_role_sort_priority)
