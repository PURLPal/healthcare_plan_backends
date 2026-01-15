# ACA API - Quick Start Guide

**Base URL:** `https://aca.purlpal-api.com/aca`

---

## 🚀 Quick Examples

### Get All States
```bash
curl "https://aca.purlpal-api.com/aca/states.json"
```

### Find Plans by ZIP Code
```bash
# All plans for Miami, FL
curl "https://aca.purlpal-api.com/aca/zip/33139.json" | jq '{plan_count, metal_levels: .plan_counts_by_metal_level}'

# Austin, TX
curl "https://aca.purlpal-api.com/aca/zip/78701.json" | jq '.plan_count'

# Phoenix, AZ  
curl "https://aca.purlpal-api.com/aca/zip/85001.json" | jq '.plan_count'
```

### Filter by Metal Level
```bash
# Silver plans only
curl "https://aca.purlpal-api.com/aca/zip/33139_Silver.json"

# Gold plans only
curl "https://aca.purlpal-api.com/aca/zip/33139_Gold.json"

# Bronze plans only
curl "https://aca.purlpal-api.com/aca/zip/33139_Bronze.json"
```

### Get Individual Plan Details
```bash
curl "https://aca.purlpal-api.com/aca/plan/13887FL0010001-00.json" | jq '{plan_name, issuer_name, metal_level}'
```

---

## 📊 Available States (30 Federal Exchanges)

AK, AL, AR, AZ, DE, FL, HI, IA, IN, KS, LA, ME, MI, MO, MS, MT, NC, ND, NE, NH, OH, OK, SC, SD, TN, TX, UT, VA, WI, WY

**Note:** States with their own exchanges (CA, NY, MA, CO, etc.) are not included.

---

## 🏥 Metal Levels

- **Bronze:** ~60% actuarial value
- **Silver:** ~70% actuarial value  
- **Gold:** ~80% actuarial value
- **Platinum:** ~90% actuarial value
- **Catastrophic:** Emergency coverage only
- **Expanded Bronze:** Enhanced Bronze plans

---

## 📱 JavaScript Example

```javascript
async function getACAPlans(zipCode) {
  const response = await fetch(
    `https://aca.purlpal-api.com/aca/zip/${zipCode}.json`
  );
  const data = await response.json();
  
  console.log(`${data.plan_count} plans available in ${zipCode}`);
  console.log('Metal levels:', data.plan_counts_by_metal_level);
  
  return data;
}

// Usage
getACAPlans('33139');
```

---

## 🐍 Python Example

```python
import requests

def get_aca_plans(zip_code, metal_level=None):
    url = f"https://aca.purlpal-api.com/aca/zip/{zip_code}"
    if metal_level:
        url += f"_{metal_level}"
    url += ".json"
    
    response = requests.get(url)
    data = response.json()
    
    print(f"{data['plan_count']} plans in {zip_code}")
    return data

# Get all plans
plans = get_aca_plans('33139')

# Get only Silver plans
silver_plans = get_aca_plans('33139', 'Silver')
```

---

## 🔍 Response Structure

```json
{
  "zip_code": "33139",
  "multi_county": false,
  "states": ["FL"],
  "primary_state": "FL",
  "counties": [
    {
      "name": "Miami-Dade County",
      "fips": "12086",
      "state": "FL",
      "ratio": 1.0,
      "plans": [...],
      "plan_count": 1858
    }
  ],
  "plans": [...],
  "plan_count": 1858,
  "plan_counts_by_metal_level": {
    "Silver": 938,
    "Gold": 364,
    "Expanded Bronze": 424,
    "Bronze": 36,
    "Platinum": 92,
    "Catastrophic": 4
  }
}
```

---

## 🔗 All Endpoints

| Endpoint | Description | Example |
|----------|-------------|---------|
| `/aca/states.json` | List all states | [Try it](https://aca.purlpal-api.com/aca/states.json) |
| `/aca/zip/{zip}.json` | Plans by ZIP | [33139](https://aca.purlpal-api.com/aca/zip/33139.json) |
| `/aca/zip/{zip}_{level}.json` | Filter by metal | [33139_Silver](https://aca.purlpal-api.com/aca/zip/33139_Silver.json) |
| `/aca/state/{ST}/info.json` | State info | [FL](https://aca.purlpal-api.com/aca/state/FL/info.json) |
| `/aca/plan/{id}.json` | Plan details | [Example](https://aca.purlpal-api.com/aca/plan/13887FL0010001-00.json) |
| `/aca/openapi.yaml` | API spec | [OpenAPI](https://aca.purlpal-api.com/aca/openapi.yaml) |

---

## ⚡ Performance

- **Response time:** 300-500ms (typical)
- **Availability:** 99.9% (AWS SLA)
- **Rate limits:** None currently
- **CORS:** Enabled for all origins

---

## 📚 Full Documentation

- **Deployment Details:** `DEPLOYMENT_SUCCESS.md`
- **Technical Guide:** `README.md`
- **API Reference:** `https://aca.purlpal-api.com/aca/openapi.yaml`

---

## 💡 Tips

1. **Use jq for pretty output:**
   ```bash
   curl "https://aca.purlpal-api.com/aca/zip/33139.json" | jq '.'
   ```

2. **Filter specific fields:**
   ```bash
   curl "https://aca.purlpal-api.com/aca/zip/33139.json" | jq '{plan_count, metal_levels: .plan_counts_by_metal_level}'
   ```

3. **Test multiple ZIPs:**
   ```bash
   for zip in 33139 78701 85001; do
     echo "$zip: $(curl -s "https://aca.purlpal-api.com/aca/zip/$zip.json" | jq -r '.plan_count') plans"
   done
   ```

---

## 🎯 Common Use Cases

### Compare Plans Across States
```bash
# Texas
curl "https://aca.purlpal-api.com/aca/state/TX/info.json"

# Florida  
curl "https://aca.purlpal-api.com/aca/state/FL/info.json"
```

### Find Cheapest Silver Plans
```bash
curl "https://aca.purlpal-api.com/aca/zip/33139_Silver.json" | \
  jq '.plans | sort_by(.rate_age_40) | .[0:5]'
```

### Get Plan Coverage in Multi-County ZIP
```bash
curl "https://aca.purlpal-api.com/aca/zip/12345.json" | \
  jq '.counties | map({name, plan_count})'
```

---

## ✅ Status

- **API Status:** ✅ Live and operational
- **Data Year:** 2026
- **Last Updated:** January 14, 2026
- **Plans:** 20,354 medical plans
- **Coverage:** 30 states (federal exchanges)
