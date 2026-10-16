# Playbook: Subprocessor Approval

**NORTHWIND SYSTEMS ENTERPRISE PLAYBOOK**
**SECTION 14: SUBPROCESSOR APPROVAL**
*Document ID: NW-PB-2026-S14*
*Author: Marcus Vance, General Counsel*
*Target Audience: Commercial Legal Team (Sarah Lin, David Chen, Elena Rostova)*

---

### 14.1 Preferred Position (Model Clause Language)

When drafting Northwind Systems as the vendor, Legal Counsel shall insert the following text into the Data Protection Addendum (DPA) without modification:

> **14.1(a) General Authorization.** Customer hereby provides a general authorization to Northwind Systems to engage third-party subprocessors to process Customer Personal Data, subject to the conditions set forth in this Section 14. Northwind Systems shall maintain a current list of its approved subprocessors at *https://www.northwindsaas.com/legal/subprocessors*, which URL shall include a subscription mechanism enabling Customer to receive automated email notifications of any intended additions or replacements of subprocessors at least thirty (30) days prior to authorizing such subprocessor to process Customer Personal Data.
>
> **14.1(b) Objection Right.** Customer may object in writing to Northwind Systems’ appointment of a new subprocessor within fourteen (14) calendar days of receiving the notification referenced in Section 14.1(a), provided such objection is based on reasonable data protection grounds. If Customer timely objects, Northwind Systems shall use commercially reasonable efforts to make available to Customer a change in the Services or recommend a commercially reasonable change to Customer’s configuration or use of the Services to avoid the processing of Customer Personal Data by the objected-to subprocessor. If Northwind Systems is unable to provide such mitigation within thirty (30) days of receipt of Customer’s objection, either party may terminate the affected Order Form(s) upon written notice, without penalty to either party, and Customer shall receive a pro-rata refund of any prepaid fees covering the remainder of the then-current subscription term for the terminated Services. This termination right shall be Customer’s sole and exclusive remedy for any objection to a subprocessor.

---

### 14.2 Fallback Position

If the counterparty rejects general authorization or demands pre-approval rights, Legal Counsel may drop to the following fallback position, subject to the operational constraints in Section 14.4:

> **14.2(a) Specific Written Notice with 20-Day Objection Window.** Northwind Systems shall provide Customer with written notice via email of any new subprocessor at least twenty (20) calendar days prior to granting that subprocessor access to Customer Personal Data.
>
> **14.2(b) Dispute Resolution and Termination.** If Customer objects to a new subprocessor on reasonable data protection grounds within the twenty (20) day period, the parties shall meet in good faith within ten (10) business days to resolve the objection. If the dispute cannot be resolved, Customer may terminate the Agreement solely with respect to the specific Service for which the subprocessor is required, upon thirty (30) days' prior written notice, subject to a monetary floor of twenty-five thousand United States Dollars ($25,000) in aggregate annual contract value for the affected Service.

---

### 14.3 Walk-Away Position

Legal Counsel **must reject** and invoke walk-away procedures if the counterparty demands any of the following terms, as they violate Northwind’s risk-tolerance thresholds:

1. **Veto / Positive Consent:** Requiring Northwind to obtain affirmative, signed written consent prior to engaging *any* subprocessor.
2. **Uncapped Liability for Subprocessor Breaches:** Making Northwind strictly liable for subprocessor acts without regard to Northwind’s standard aggregate liability cap.
3. **Immediate Injunction Rights:** Permitting Customer to seek ex parte injunctive relief to halt core SaaS infrastructure processing upon subprocessor notification.

---

### 14.4 Numeric and Categorical Thresholds

Legal Counsel shall strictly enforce the following parameters during contract negotiations:

* **Threshold 1 (Notice Period):** Minimum preferred notice period is thirty (30) days; absolute contractual floor is twenty (20) calendar days. Never accept fewer than twenty (20) days.
* **Threshold 2 (Cure/Mitigation Period):** Thirty (30) calendar days for Northwind to find an alternative technical workaround or mitigation following a customer objection.
* **Threshold 3 (Monetary Floor for Termination):** Customer may only terminate for subprocessor objection if the Annual Contract Value (ACV) of the affected subscription meets or exceeds twenty-five thousand United States Dollars ($25,000). Accounts below $25,000 ACV must accept the subprocessor or terminate under standard convenience terms (subject to forfeiture of prepaid fees).
* **Threshold 4 (Subprocessor Indemnity/Liability Cap Multiplier):** If a counterparty insists on super-cap liability for subprocessor data breaches, the absolute maximum liability cap negotiable is **two times (2x)** the total fees paid by Customer in the preceding twelve (12) months, or one hundred thousand United States Dollars ($100,000), whichever is greater.

---

### 14.5 Named Deviations Requiring Escalation

Legal Counsel may not autonomously agree to the following deviations; each requires written approval from the designated corporate officer:

1. **Deviation A (Exclusion of Core Infrastructure Partners):** Customer demands the right to individually approve or restrict Amazon Web Services (AWS) or Snowflake as primary cloud infrastructure sub-processors. 
   * *Escalation Target:* **Chief Technology Officer (CTO), Arthur Pendelton.** (Infrastructure changes require architectural sign-off).
2. **Deviation B (Refund Multiplier Exceeding Standard Terms):** Customer negotiates a full refund of *all* historical fees paid under the Agreement (rather than pro-rata prepaid fees for the remainder of the term) upon subprocessor termination.
   * *Escalation Target:* **Chief Financial Officer (CFO), Brenda Sterling.** (P&L impact review required).
3. **Deviation C (Custom Subprocessor Audit Rights):** Customer demands the right to directly audit Northwind’s subprocessors on-site at Northwind's expense.
   * *Escalation Target:* **General Counsel, Marcus Vance.** (Vendor contract compliance risk).

---

### 14.6 Worked Examples of Counterparty Language

#### Acceptable Counterparty Language (Approved for Inclusion)

*Example 1 (Acceptable Alternative Notice Mechanism):*
> "Provider shall maintain an online portal listing all subprocessors and shall notify Customer via email update to admin@customer.com at least thirty (30) days prior to authorizing any new subprocessor to process Customer Personal Data. Customer may object on legitimate privacy grounds within twenty (20) days of such notice."
*Rationale:* Extends notice window favorably for Customer while maintaining the online notification mechanism and reasonable objection grounds.

*Example 2 (Acceptable Mutual Mitigation Language):*
> "In the event of a timely objection by Customer to a new subprocessor, the parties shall cooperate in good faith for a period of thirty (30) days to implement a commercially reasonable workaround that avoids data transfer to the objected-to subprocessor."
*Rationale:* Explicitly codifies the good-faith mitigation period without imposing punitive financial penalties or strict liability on Northwind.

#### Unacceptable Counterparty Language (Must Be Deleted/Redlined)

*Example 1 (Unacceptable Positive Consent Requirement):*
> "Vendor shall not engage any subprocessor to process Customer Personal Data without the prior express written consent of Customer, which consent shall not be unreasonably withheld, delayed, or conditioned."
*Rationale:* Violates preferred position (14.1) by destroying general authorization and introducing operational gridlock. Must be redlined back to Section 14.1.

*Example 2 (Unacceptable Uncapped Indemnity):*
> "Vendor shall indemnify, defend, and hold harmless Customer from and against any and all losses, damages, and regulatory fines arising out of or relating to any act or omission of any subprocessor engaged by Vendor, without regard to any limitation of liability or liability cap set forth in the Agreement."
*Rationale:* Violates walk-away criteria (14.3) and threshold parameters (14.4). Exposes Northwind to uninsurable, uncapped pass-through liability for third-party vendor failures.
