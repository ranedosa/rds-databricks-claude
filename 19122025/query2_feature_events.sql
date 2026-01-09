-- Query 2: Check feature events for Park Kennedy
SELECT
    pfe.property_id,
    p.name,
    pfe.feature_code,
    pfe.event_type,
    pfe.inserted_at,
    pfe._fivetran_deleted,
    ROW_NUMBER() OVER (PARTITION BY pfe.property_id, pfe.feature_code ORDER BY pfe.inserted_at DESC) as event_rank
FROM property_feature_events pfe
JOIN properties p ON p.id = pfe.property_id
WHERE p.name LIKE '%Park Kennedy%'
ORDER BY pfe.property_id, pfe.feature_code, pfe.inserted_at DESC
LIMIT 50;
