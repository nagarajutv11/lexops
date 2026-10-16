# Playbook: Service Levels and Service Credits

**NORTHWIND SYSTEMS INTERNAL LEGAL PLAYBOOK**
**SECTION 12: SERVICE LEVELS AND SERVICE CREDITS**

---

### 12.1 PREFERRED NORTHWIND POSITION (MODEL CLAUSE LANGUAGE)

> **12.1.1 Service Availability.** Northwind shall use commercially reasonable efforts to make the SaaS Platform available with an uptime percentage of at least 99.5% during each calendar month (the "Service Commitment"), excluding scheduled maintenance, emergency maintenance, and Excused Downtime.
>
> **12.1.2 Measurement.** Availability shall be calculated as: $\frac{(Total Minutes - Downtime)}{Total Minutes} \times 100$. "Downtime" means the total accumulated minutes during a calendar month during which the SaaS Platform is entirely unavailable to Customer, excluding Excluded Outages.
>
> **12.1.3 Excluded Outages.** "Excused Downtime" means downtime resulting from: (a) scheduled maintenance communicated at least forty-eight (48) hours in advance; (b) emergency maintenance; (c) Customer's acts, omissions, or breach of the Agreement; (d) failure of Customer's internet connection, hardware, or third-party software; or (e) Force Majeure events.
>
> **12.1.4 Service Credits.** If the Service Commitment is not met in any two (2) consecutive calendar months, Customer's sole and exclusive remedy, and Northwind's sole and entire liability, shall be to claim a service credit calculated as 5% of the monthly equivalent of the annual subscription fees for that month, credited against future invoices. Service credits shall never exceed 15% of the total annual subscription fees paid by Customer in the applicable contract year.
>
> **12.1.5 Credit Claim Procedure.** To receive a service credit, Customer must submit a written claim via Northwind’s support portal within thirty (30) days following the end of the month in which the Service Commitment was missed. Failure to comply shall forfeit the right to any credit. Service credits are non-refundable, non-exchangeable, and expire upon termination of the Agreement.
>
> **12.1.6 Sole Remedy.** Service credits are liquidated damages and represent Customer’s sole remedy for any failure by Northwind to meet the Service Commitment.

---

### 12.2 FALLBACK POSITION

*Use only if Customer rejects the 99.5% availability threshold or the two-consecutive-month requirement, and Customer ARR exceeds $150,000.*

> **12.2.1 Adjusted Commitment.** The uptime percentage may be adjusted to **99.9%** per calendar month.
>
> **12.2.2 Single-Month Trigger.** Remove the requirement for two consecutive months; credits apply for any single calendar month where uptime falls below 99.9%.
>
> **12.2.3 Tiered Credit Structure:**
> * Uptime between 99.0% and 99.89%: 5% of monthly fees.
> * Uptime between 95.0% and 98.99%: 10% of monthly fees.
> * Uptime below 95.0%: 20% of monthly fees.
>
> **12.2.4 Aggregate Annual Cap.** The annual cap on service credits remains strictly capped at **15%** of the annual subscription fee.
>
> **12.2.5 Claim Window.** The notice period for claiming credits may be extended from thirty (30) days to **forty-five (45) days** following the end of the affected month.
>
> **12.2.6 Cure Period.** Northwind shall have **thirty (30) days** from receipt of a credit claim to cure any underlying recurring performance defect before any credit is applied to an invoice.

---

### 12.3 WALK-AWAY POSITION

*Legal team must cease negotiations and escalate or terminate discussions if Customer demands any of the following:*

1. Uptime availability commitments exceeding **99.95%** (excluding standard maintenance windows).
2. Annual or per-incident service credit caps exceeding **25%** of annual subscription fees, or any provision allowing service credits to be paid out as cash refunds.
3. Monthly compounding of service credits or failure to include a monetary floor where credits below **$500.00** per claim are explicitly excluded.
4. Definition of "Downtime" that includes degradation of performance (latency) rather than complete non-availability, or exclusion of scheduled maintenance from the maintenance window carve-out.

---

### 12.4 SPECIFIC NUMERIC AND CATEGORICAL THRESHOLDS

* **Standard Uptime Target:** 99.5% monthly availability.
* **Fallback Uptime Target:** 99.9% monthly availability.
* **Maximum Annual Credit Cap:** 15% of annual contract value (ACV).
* **Maximum Single-Incident Credit Cap:** 5% of annual contract value.
* **Customer Claim Notice Period:** 30 days (Preferred) / 45 days (Fallback) from month-end.
* **Scheduled Maintenance Notice Period:** 48 hours in advance.
* **Technical Cure Period:** 30 days following receipt of notice.
* **Monetary Floor per Claim:** $500.00 (Credits amounting to less than $500.00 in a given month are void and non-accumulative).

---

### 12.5 NAMED DEVIATIONS REQUIRING ESCALATION

The following structural deviations from the playbook require prior written approval from the designated corporate officer before submission to Customer:

1. **Cash Refund Requests:** Any agreement permitting service credits to be converted into cash refunds or offset against professional services invoices requires escalation to **Chief Financial Officer, Martha Vance**.
2. **Exclusion of Maintenance Windows:** Any removal or restriction of Northwind's right to perform scheduled maintenance without incurring downtime penalties requires escalation to **VP of Engineering, Arthur Pendelton**.
3. **Custom Uptime SLAs Above 99.9%:** Any contractual uptime commitment above 99.9% for customers with an ACV under $250,000 requires escalation to **General Counsel, Sarah Jenkins**.

---

### 12.6 WORKED EXAMPLES OF COUNTERPARTY LANGUAGE

#### Acceptable Counterparty Language (Approved for use with minor grammatical adjustments)

* **Example A1 (Tiered Structure with Cap):**
  > "If Northwind fails to achieve 99.9% availability in any calendar month, Customer shall receive a credit equal to 10% of the monthly fee for each full percentage point of deficiency, up to a maximum annual aggregate credit of 15% of the annual fee, provided Customer requests such credit in writing within forty-five (45) days of the end of the applicable month."
  > *Analysis:* Acceptable under Fallback Position. It establishes a tiered model, respects the 15% annual cap, and stays within the 45-day notice window.

* **Example A2 (Monetary Floor Inclusion):**
  > "Service credits shall be applied solely against future invoices and are Customer's sole remedy for availability failures. No credit shall be issued under this Section if the calculated credit amount is less than $500.00."
  > *Analysis:* Acceptable. It protects Northwind from micro-claims and reinforces the exclusive remedy principle.

#### Unacceptable Counterparty Language (Must be rejected by Legal)

* **Example U1 (Cash Refund and Excess Cap):**
  > "If the SaaS Platform is unavailable for more than four hours in any given quarter, Customer may terminate this Agreement for material breach and demand an immediate cash refund of all pre-paid fees for the remainder of the subscription term, plus a 30% service penalty."
  > *Analysis:* Unacceptable. Violates the walk-away position by introducing termination rights for standard SLA breaches, cash refunds, and exceeds the 15% annual credit cap.

* **Example U2 (Performance Degradation and No Cap):**
  > "Downtime includes any period where page load times exceed two seconds. Northwind shall credit 50% of the monthly subscription fee for each occurrence of latency, with no aggregate annual limitation on credits."
  > *Analysis:* Unacceptable. Re-defines downtime to include subjective latency metrics, imposes excessive credit multipliers, and omits the mandatory annual cap.
