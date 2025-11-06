import requests


# url = "https://demo-enterprise-api.snappt.com/properties"
sandbox_url = "https://enterprise-api.test.snappt.com/properties"

df = spark.sql("""
               SELECT 
               company_id_c as sf_company_id, 
               company_name_c as sf_account_name,
               id as sf_property_id,
               name as sf_property_name,
            --    concat_ws(',', address_street_s, address_city_s, address_postal_code_s) as sf_property_address,
               address_street_s,
               address_city_s,
               address_postal_code_s,
               unit_c as sf_property_unit_count,
               email_c as sf_property_manager_email,
               status_c as sf_property_status
               FROM hive_metastore.salesforce.product_property_c 
               where sf_property_id_c = 'a01Dn00000HHNKjIAP'
               limit 10
               """)
df_json = df.toPandas().to_dict(orient='records')

payload = {
    "status": df_json[0]['sf_property_status'],
    "name": df_json[0]['sf_property_name'],
    "email": df_json[0]['sf_property_manager_email'],
    "address": df_json[0]['address_street_s'],
    "city": df_json[0]['address_city_s'],
    "zip": df_json[0]['address_postal_code_s'],
    "unit": df_json[0]['sf_property_unit_count'],
    "pmcName": "enterprise api company"
}
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "Authorization": "Bearer 5f5770c2-0563-11ee-be56-0242ac120003"
}

response = requests.post(sandbox_url, json=payload, headers=headers)

print(response.text)