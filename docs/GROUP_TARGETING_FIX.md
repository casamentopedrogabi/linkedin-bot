# 🎯 Group Connection Targeting Fix - February 21, 2026

## Problem Identified
Bot was collecting **52 profiles from groups** but only attempting **1-2 connections**. Issue: Group profiles don't match the strict `TARGET_ROLES` list (CEO, CTO, VP positions), so they were only being followed for SSI boost, not connected.

## Root Cause
- **TARGET_ROLES** = Very selective (CTO, VP, Lead Data Scientist, etc.)
- **Group members** = Mostly mid-level engineers, analysts, developers
- **Result** = Profile filtering was TOO RESTRICTIVE for group networking

---

## Solution Implemented

### 1. ✅ Added GROUP_TARGET_KEYWORDS (Lines 146-193)
A **44+ keyword list** specifically for group targeting, much more inclusive:
- **Data & Analytics**: data scientist, engineer, ml engineer, python, sql, etc.
- **Cloud & Infrastructure**: aws, azure, gcp, devops, kubernetes, docker
- **AI/Emerging Tech**: artificial intelligence, generative ai, nlp, llm
- **Senior Levels**: senior, lead, staff, principal, manager, architect
- **Technical Skills**: software engineer, backend, frontend, react, node, java

### 2. ✅ Updated Connection Logic (Lines 1430-1480)
Split targeting into two strategies:
```python
# For SNIPER targets: Use strict TARGET_ROLES (executives only)
is_sniper_target = any(role in headline for role in TARGET_ROLES)

# For GROUP targets: Use inclusive GROUP_TARGET_KEYWORDS
is_group_target = any(keyword in headline for keyword in GROUP_TARGET_KEYWORDS)
```

### 3. ✅ Increased Connection Limits
- **CONNECTION_LIMIT**: `15-16` → **`20-25`** (+30% capacity)
- **QUICK_CONNECT_RATE**: `50/50 split` → **`30/70 split`** (more weight to groups)
  - Sniper: 30% (6-7 connections)
  - Group: 70% (14-18 connections)

### 4. ✅ Added Debug Logging
When `VERBOSE=True`, prints matches:
```
-> [GROUP MATCH] Headline matches keywords: senior data scientist at...
```

---

## Expected Results

### Before Fix
- 52 profiles collected ✓
- ~1 connection attempted ✗
- Most profiles only followed for SSI ⚠️

### After Fix
- 52 profiles collected ✓
- **~14-18 connection attempts** (using GROUP keywords)
- Smarter targeting: Connect with genuine prospects, follow influencers

---

## Configuration Summary

| Setting | Before | After | Impact |
|---------|--------|-------|--------|
| CONNECTION_LIMIT | 15-16 | 20-25 | +30% |
| SNIPER_RATE | 50% | 30% | More group focus |
| GROUP_RATE | 50% | 70% | Better group ROI |
| TARGET_ROLES | Only strict | + GROUP_KEYWORDS | Vastly more inclusive |

---

## Next Steps

1. **Test with next group run** - Bot should now attempt 14-18+ connections from groups
2. **Monitor headlines** - Check if GROUP_MATCH debug lines appear regularly
3. **Adjust keywords** - If headlines still don't match, add more keywords to GROUP_TARGET_KEYWORDS
4. **Check connection success rate** - Monitor acceptance rate for group connections

---

## Technical Notes

- **Backward compatible**: Sniper mode still uses strict TARGET_ROLES
- **No breaking changes**: All existing checks remain in place
- **Safe scaling**: Rates are configurable via QUICK_CONNECT_RATE
- **Debugging**: VERBOSE mode shows which profiles match keywords

---

**Example Profiles Now Targeted (Group)**
- "Senior Data Scientist at XYZ" ✓ matches "senior", "data scientist"
- "ML Engineer (NLP Focus)" ✓ matches "ml engineer", "nlp"
- "Backend Developer | Python | AWS" ✓ matches "backend", "python", "aws"
- "Full Stack Engineer at Startup" ✓ matches "full stack", "engineer"
- "Analytics Manager, SQL/Tableau" ✓ matches "analytics", "manager", "sql"

---

**Last Updated**: February 21, 2026
**Status**: ✅ Ready to Test
