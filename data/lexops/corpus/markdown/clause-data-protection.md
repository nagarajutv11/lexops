# Playbook: Data Protection and Processing

# NORTHWIND SYSTEMS LEGAL PLAYBOOK
## SECTION 8: DATA PROTECTION AND PROCESSING (INTERNAL USE ONLY)

### 8.1 Scope and Application
This Section 8 governs all Data Processing Addenda (DPAs) attached to Master Services Agreements (MSAs) or Enterprise Software Agreements entered into by Northwind Systems, Inc. ("Northwind") as a Processor of Customer Personal Data. No attorney may approve terms outside these parameters without formal escalation under Section 8.5.

---

### 8.2 Preferred Position (Model Clause Language)

#### 8.2.1 Standard DPA Incorporation
> "The parties agree that the Northwind Systems Standard Data Processing Addendum, version 4.2, available at https://legal.northwind.com/dpa-v42, is hereby incorporated by reference into this Agreement. In the event of any conflict between the terms of this Agreement and the Data Processing Addendum, the Data Processing Addendum shall control solely with respect to the processing of Customer Personal Data."

#### 8.2.2 Limitation of Liability (Data Protection)
> "Northwind’s total aggregate liability arising out of or related to breaches of Section 8 (Data Protection) and the Data Processing Addendum, whether in contract, tort (including negligence), or under any other theory of liability, shall be strictly capped at **one hundred percent (100%)** of the total fees paid or payable by Customer to Northwind under the applicable Order Form in the **twelve (12) month** period preceding the event giving rise to liability, subject to the overall limitation of liability cap set forth in the main body of this Agreement."

#### 8.2.3 Security Incident Notification
> "Northwind shall notify Customer without undue delay, and in any event no later than **seventy-two (72) hours**, after becoming aware of a confirmed Security Incident impacting Customer Personal Data, providing such notification to the designated Customer security contact via email."

#### 8.2.4 Audit Rights
> "Customer may audit Northwind’s compliance with its data protection obligations once per calendar year upon **thirty (30) days’** prior written notice, during normal business hours, at Customer’s sole expense, utilizing an independent third-party auditor mutually agreed upon by the parties."

---

### 8.3 Fallback Position

If the counterparty rejects the Preferred Position, attorneys are authorized to negotiate down to the following fallback thresholds:

*   **Liability Cap:** May be increased up to **two hundred percent (200%)** of the preceding 12 months' fees, or a monetary floor of **$250,000 USD**, whichever is greater.
*   **Incident Notification:** May be shortened to **forty-eight (48) hours**.
*   **Audit Notice Period:** May be reduced to **fourteen (14) days**, provided the audit is conducted by a certified public accounting firm bound by professional confidentiality standards.
*   **Cure Period:** A cure period of **thirty (30) days** must be inserted for any material breach of the DPA prior to Customer exercising termination rights.

---

### 8.4 Walk-Away Position

Attorneys must terminate negotiations or refuse counterparty language if any of the following conditions are demanded:

1.  **Uncapped Liability:** Any demand for unlimited liability, or liability capped at a multiple exceeding **three hundred percent (300%)** of contract value, for data security breaches.
2.  **Unilateral Direct Audits:** Any right for Customer’s internal employees or non-certified consultants to physically inspect Northwind’s production servers, data centers, or source code.
3.  **Indemnification for Regulatory Fines:** Any requirement for Northwind to directly indemnify Customer for administrative fines issued by supervisory authorities under GDPR, CCPA, or equivalent privacy statutes (fines must remain subject to the contractual liability cap).
4.  **Immediate Deletion on Demand:** Any clause requiring the return or certified deletion of Customer Personal Data prior to the expiration of Northwind’s statutory data retention and backup tape recycling cycles (maximum **ninety (90) days** post-termination).

---

### 8.5 Named Deviations and Escalation Matrix

The following specific deviations from the Playbook require formal written sign-off from the named internal stakeholder before execution:

1.  **Subprocessor Objection Period Exceeding 14 Days:** If a counterparty demands more than **fourteen (14) days** to object to the appointment of a new subprocessor, or demands the right to terminate the contract without penalty upon subprocessor objection.
    *   *Escalate to:* **Marcus Vance, VP of Engineering.**
2.  **Cross-Border Data Transfer Mechanisms (Non-SCCs):** If a counterparty refuses Northwind’s standard EU Standard Contractual Clauses (SCCs) and demands customized local data localization terms or non-standard transfer frameworks.
    *   *Escalate to:* **Elena Rostova, Chief Information Security Officer.**
3.  **Insurance Requirement Deviations for Data Processing:** If a counterparty demands Cyber Liability Insurance coverage limits exceeding Northwind’s standard policy limit of **$5,000,000 USD** per occurrence.
    *   *Escalate to:* **Sarah Jenkins, Chief Financial Officer.**

---

### 8.6 Worked Examples of Counterparty Language

#### 8.6.1 Acceptable Counterparty Language (Passes Review)

*   **Example A (Incident Notification):**
    > *"Processor shall notify Controller without undue delay, and in no event later than forty-eight (48) hours, upon confirming any unauthorized acquisition of Customer Personal Data."*
    *   *Analysis:* Acceptable. Falls within the fallback parameter of 48 hours (stricter than preferred 72 hours, but operationally achievable).

*   **Example B (Liability Cap):**
    > *"Subject to Section 12, the total aggregate liability of Northwind for all claims arising out of the Data Processing Addendum shall not exceed one hundred fifty percent (150%) of the fees paid by Customer in the preceding twelve months."*
    *   *Analysis:* Acceptable. 150% sits comfortably between the preferred position (100%) and the walk-away threshold (300%).

#### 8.6.2 Unacceptable Counterparty Language (Fails Review — Reject)

*   **Example C (Uncapped Liability for Data Breaches):**
    > *"The limitations and exclusions of liability set forth in this Agreement shall not apply to any breach of Section 8 (Data Protection) or any unauthorized disclosure of Customer Personal Data, for which Processor's liability shall be completely uncapped."*
    *   *Analysis:* Unacceptable. Violates Section 8.4(1) (Walk-away position: Uncapped liability). Must be countered with the preferred or fallback liability cap.

*   **Example D (Direct On-Site Inspection):**
    > *"Customer or its designated regulatory representatives may enter Northwind’s physical facilities and data centers at any time during normal business hours to conduct unannounced penetration testing and hardware inspections of servers processing Customer data."*
    *   *Analysis:* Unacceptable. Violates Section 8.4(2) (Walk-away position: Unilateral direct audits) and creates severe SOC 2 compliance and multi-tenant security risks. Must be restricted to third-party paper audits or certified SOC 2 reports.
