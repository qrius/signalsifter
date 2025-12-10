# Discord Extraction - Week-Long Validation Test Plan

## 🎯 **Objective:** 
Validate Discord extraction accuracy over 1 week duration to ensure:
- Complete message capture 
- Accurate content extraction
- Proper username/timestamp handling
- Reliable data quality

## 📊 **Current Status Review**
✅ Database schema ready (empty state)  
❌ Dry run shows missing content & usernames (needs selector fixes)  
❌ Need to fix extraction before validation testing  

## 🔧 **Pre-Test Requirements**

### 1. **Fix Current Extraction Issues**
Based on latest dry run (`discord_extraction_dry_run_20251209_164033.json`):
- ❌ `content`: Empty strings
- ❌ `username`: "Unknown" 
- ❌ `user_id`: "Unknown"
- ✅ `message_id`: Working (content-1447729446449582100)
- ✅ `timestamp`: Working (2025-12-08 23:20:19.355000+00:00)

**Action Required:** Debug and fix selectors before validation test

### 2. **Validation Test Parameters**
```bash
# Test Duration: 1 week (7 days)
# Start Date: Current - 7 days
# Channel: https://discord.com/channels/1296015181985349715/1296015182417629249
# Expected Volume: ~100-500 messages (estimated)
```

## 📋 **Validation Test Plan**

### **Phase 1: Quick Fix Verification (30 minutes)**
1. **Debug Current Selectors:**
   ```bash
   source signalsifter-env/bin/activate
   python3 debug_discord_selectors.py
   ```

2. **Test Small Sample:**
   ```bash
   python3 discord_browser_extractor.py --url "https://discord.com/channels/1296015181985349715/1296015182417629249" --limit 3 --dry-run --verbose
   ```

3. **Verify Fix:**
   - Content should not be empty
   - Usernames should not be "Unknown"
   - Message structure should be complete

### **Phase 2: Week-Long Extraction Test (2-3 hours)**
1. **Full Week Extraction:**
   ```bash
   python3 discord_browser_extractor.py \
     --url "https://discord.com/channels/1296015181985349715/1296015182417629249" \
     --days 7 \
     --verbose \
     --save-to-db
   ```

2. **Live Monitoring:**
   ```bash
   # Monitor extraction progress
   watch -n 30 'sqlite3 data/backfill.sqlite "SELECT COUNT(*) FROM discord_messages;"'
   ```

### **Phase 3: Data Quality Validation**

#### **A. Completeness Checks**
```sql
-- Total message count
SELECT COUNT(*) as total_messages FROM discord_messages;

-- Messages with content
SELECT COUNT(*) as messages_with_content 
FROM discord_messages 
WHERE content IS NOT NULL AND content != '';

-- Unique users
SELECT COUNT(DISTINCT username) as unique_users 
FROM discord_messages 
WHERE username != 'Unknown';

-- Date range coverage
SELECT 
    MIN(DATE(timestamp)) as earliest_date,
    MAX(DATE(timestamp)) as latest_date,
    COUNT(DISTINCT DATE(timestamp)) as days_covered
FROM discord_messages;
```

#### **B. Data Quality Checks**
```sql
-- Check for missing critical fields
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN content = '' OR content IS NULL THEN 1 END) as empty_content,
    COUNT(CASE WHEN username = 'Unknown' OR username IS NULL THEN 1 END) as missing_usernames,
    COUNT(CASE WHEN timestamp IS NULL THEN 1 END) as missing_timestamps
FROM discord_messages;

-- Check for duplicates
SELECT message_id, COUNT(*) as count 
FROM discord_messages 
GROUP BY message_id 
HAVING COUNT(*) > 1;

-- Check timestamp distribution (should be evenly distributed over 7 days)
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as message_count
FROM discord_messages 
GROUP BY DATE(timestamp)
ORDER BY date;
```

#### **C. Content Validation Sampling**
```sql
-- Sample recent messages for manual review
SELECT 
    username,
    SUBSTR(content, 1, 50) as content_preview,
    timestamp,
    LENGTH(content) as content_length
FROM discord_messages 
WHERE content != '' 
ORDER BY timestamp DESC 
LIMIT 10;

-- Check for suspicious patterns
SELECT 
    'Very short messages' as check_type,
    COUNT(*) as count
FROM discord_messages 
WHERE LENGTH(content) < 3 AND content != ''
UNION ALL
SELECT 
    'Very long messages' as check_type,
    COUNT(*) as count
FROM discord_messages 
WHERE LENGTH(content) > 2000;
```

## 📊 **Success Criteria**

### **Must Have (Critical):**
- ✅ **Message Count:** > 50 messages (minimum viable)
- ✅ **Content Completeness:** > 80% of messages have non-empty content
- ✅ **Username Accuracy:** > 90% of messages have valid usernames (not "Unknown")
- ✅ **Date Coverage:** At least 5 out of 7 days should have messages
- ✅ **No Critical Errors:** Zero database constraints violations

### **Should Have (Quality):**
- ✅ **Message Count:** > 100 messages (good volume)
- ✅ **Content Completeness:** > 95% of messages have non-empty content
- ✅ **Duplicate Rate:** < 5% duplicate messages
- ✅ **Timestamp Accuracy:** All timestamps within expected date range

### **Nice to Have (Excellence):**
- ✅ **Rich Data:** Proper handling of reactions, embeds, mentions
- ✅ **User Details:** Accurate user_id extraction
- ✅ **Thread Support:** Proper parent_id/thread_id handling

## 🚨 **Failure Scenarios & Troubleshooting**

### **Scenario 1: Empty Content**
**Symptoms:** Most messages have empty `content` field  
**Likely Cause:** CSS selectors outdated  
**Fix:** Update selectors in `discord_browser_extractor.py`

### **Scenario 2: "Unknown" Usernames**
**Symptoms:** Most messages show username as "Unknown"  
**Likely Cause:** Username selectors not matching current Discord DOM  
**Fix:** Debug with `debug_discord_selectors.py` and update selectors

### **Scenario 3: Low Message Count**
**Symptoms:** < 50 messages extracted  
**Likely Cause:** Scrolling not working or date filtering issues  
**Fix:** Check scrolling logic and date range parameters

### **Scenario 4: Authentication Issues**
**Symptoms:** Extraction fails or returns no data  
**Likely Cause:** Discord session expired  
**Fix:** Re-authenticate through browser automation

## 📁 **Generated Artifacts**

During validation test, the following files will be created:
- `data/backfill.sqlite` - Main database with extracted messages
- `logs/discord_extraction_week_validation_YYYYMMDD.log` - Detailed extraction log
- `validation_report_YYYYMMDD.json` - Automated validation results
- `week_validation_results.md` - Human-readable summary

## ⏰ **Estimated Timeline**

| Phase | Duration | Description |
|-------|----------|-------------|
| **Phase 1** | 30 minutes | Fix selectors, test small sample |
| **Phase 2** | 2-3 hours | Full week extraction |
| **Phase 3** | 1 hour | Data validation & analysis |
| **Total** | **3.5-4.5 hours** | Complete validation test |

## 🎯 **Next Actions**

1. **IMMEDIATE:** Fix current selector issues (content & username)
2. **THEN:** Run full week validation test
3. **FINALLY:** Generate validation report and update documentation

---

**Created:** December 9, 2025  
**Status:** Ready to Execute (pending selector fixes)  
**Channel:** 1296015182417629249 (Galactic Mining Club)