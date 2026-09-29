# Sample Q&A

Captured after local ingest. Re-run `python ingest.py` and `python -c "from rag.pipeline import ask; ..."` if pages change.

Facts-only. Not investment advice.

---

### 1. Expense ratio (Large Cap)

**Q:** What is the expense ratio of HDFC Large Cap Fund (Direct)?

**A:** *(filled after ingest — if the HTML page has no TER, the assistant should say it is not in the indexed pages and still cite a source.)*

**Source:** https://www.hdfcfund.com/explore/mutual-funds/hdfc-large-cap-fund/direct

---

### 2. Exit load

**Q:** What is the exit load for HDFC Flexi Cap Fund (Direct)?

**A:** *(after ingest)*

**Source:** https://www.hdfcfund.com/explore/mutual-funds/hdfc-flexi-cap-fund/direct

---

### 3. Minimum SIP

**Q:** What is the minimum SIP for HDFC Mid Cap Fund (Direct)?

**A:** *(after ingest)*

**Source:** https://www.hdfcfund.com/explore/mutual-funds/hdfc-mid-cap-fund/direct

---

### 4. ELSS lock-in

**Q:** What is the lock-in for HDFC ELSS Tax Saver Fund?

**A:** *(after ingest)*

**Source:** https://www.hdfcfund.com/explore/mutual-funds/hdfc-elss-tax-saver-fund/direct

---

### 5. Riskometer / benchmark

**Q:** What is the riskometer and benchmark of HDFC Balanced Advantage Fund (Direct)?

**A:** *(after ingest)*

**Source:** https://www.hdfcfund.com/explore/mutual-funds/hdfc-balanced-advantage-fund/direct

---

### 6. Capital gains statement

**Q:** How do I download a capital gains statement?

**A:** *(after ingest)*

**Source:** https://www.hdfcfund.com/learn/blog/how-get-capital-gain-statement-mutual-fund-schemes-india

---

### 7. Advice refusal

**Q:** Should I buy HDFC Flexi Cap Fund?

**A:** I cannot advise whether you should buy, sell, or switch a scheme. This tool only shares facts from official public pages, not investment advice.

**Source:** https://www.amfiindia.com/investor-corner

---

### 8. Returns refusal

**Q:** Which of these funds performed better last year?

**A:** I do not compute or compare returns. Use the official factsheet for scheme performance and related disclosures.

**Source:** https://www.hdfcfund.com/mutual-funds/factsheets

---

### 9. Out of scope

**Q:** What is the expense ratio of SBI Bluechip?

**A:** That scheme or AMC is out of scope. I only cover these HDFC Direct schemes: HDFC Flexi Cap Fund; HDFC Large Cap Fund; HDFC ELSS Tax Saver Fund; HDFC Mid Cap Fund; HDFC Balanced Advantage Fund.

**Source:** https://www.amfiindia.com/investor-corner

---

### 10. Unknown / not in corpus

**Q:** What is the fund manager's favourite stock in the mid cap scheme?

**A:** I do not have this in the official pages I indexed. Try naming one of the five HDFC Direct schemes, or check the factsheet hub.

**Source:** https://www.hdfcfund.com/mutual-funds/factsheets
