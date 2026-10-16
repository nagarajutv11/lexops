# Playbook: Force Majeure

# NORTHWIND SYSTEMS INTERNAL LEGAL PLAYBOOK
## SECTION 14: FORCE MAJEURE

---

### 14.1 Preferred Northwind Position (Model Clause Language)

14.1.1 **Definition of Force Majeure.** Neither Party shall be liable for any failure or delay in the performance of its obligations under this Agreement (excluding the obligation to pay fees accrued prior to the event) to the extent such failure or delay is caused by events beyond that Party’s reasonable control, limited strictly to: acts of God, flood, fire, earthquake, explosion, war, terrorism, invasion, riot, national state of emergency, pandemic or epidemic officially declared by the World Health Organization or the federal government, and disruption of utility services or telecommunications infrastructure extending beyond forty-eight (48) continuous hours, provided that such event was not foreseeable, could not have been avoided through the implementation of commercially reasonable disaster recovery and business continuity measures, and did not result from the fault or negligence of the affected Party ("Force Majeure Event").

14.1.2 **Exclusions.** For the avoidance of doubt, economic hardship, changes in market conditions, currency fluctuations, labor strikes internal to the affected Party, supplier price increases, or equipment failure not caused by an independent Force Majeure Event shall not constitute a Force Majeure Event.

14.1.3 **Notice Requirement.** The Party claiming relief under this Section 14 (the "Affected Party") shall notify the other Party in writing within three (3) business days of the commencement of the Force Majeure Event, detailing the specific nature of the event, its expected duration, and the obligations impacted.

14.1.4 **Mitigation Obligations.** The Affected Party shall use all commercially reasonable efforts to mitigate the operational and financial impact of the Force Majeure Event, resume performance of its obligations as expeditiously as possible, and provide weekly written status updates to the unaffected Party.

14.1.5 **Termination Right.** If a Force Majeure Event prevents, hinders, or delays the Affected Party's performance for a continuous period exceeding thirty (30) calendar days, the unaffected Party may terminate this Agreement immediately upon written notice without penalty, liability, or further obligation, subject only to the payment of fees for services rendered prior to the onset of the Force Majeure Event.

---

### 14.2 Fallback Position

14.2.1 If the counterparty rejects the preferred 30-day termination threshold, Legal Counsel is authorized to accept a termination threshold of forty-five (45) calendar days, provided that the notice period for invoking the clause remains strictly at three (3) business days.

14.2.2 If the counterparty insists on including "strikes or other industrial disputes" as a Force Majeure Event, Legal Counsel may accept this addition *only if* it explicitly excludes strikes, lockouts, or labor disputes involving the internal workforce, contractors, or unionized personnel of the Affected Party.

---

### 14.3 Walk-Away Position

14.3.1 Legal Counsel must break negotiations or reject any clause that incorporates any of the following terms:
* (a) Inclusion of economic downturn, inflation, or supply chain cost escalation within the definition of Force Majeure.
* (b) A Force Majeure termination threshold exceeding sixty (60) calendar days without an unmitigated right for Northwind to terminate for convenience upon thirty (30) days' notice.
* (c) Waiver of Northwind’s right to invoice and collect fees for software-as-a-service (SaaS) subscription tiers that remained accessible during the partial duration of the event.
* (d) Any clause that relieves the counterparty of payment obligations for services already delivered, regardless of the duration or severity of the Force Majeure Event.

---

### 14.4 Numeric and Categorical Thresholds

* **Notice Period:** Three (3) business days from the onset of the event for initial written notification to the unaffected Party.
* **Cure / Performance Suspension Period:** Forty-five (45) calendar days maximum aggregate suspension of service delivery before the unaffected Party holds an unconditional right of termination.
* **Monetary Floor:** Five Thousand US Dollars ($5,000.00) in aggregate unrecoverable operational loss per event before Northwind initiates internal cost-allocation tracking.
* **Liability Cap Multiplier:** Force Majeure relief shall not excuse any liability exceeding one hundred and fifty percent (150%) of the total SaaS subscription fees paid or payable by the customer to Northwind in the preceding twelve (12) month period preceding the event.

---

### 14.5 Named Deviations Requiring Escalation

The following deviations from the preferred or fallback positions require written approval prior to contract execution:

14.5.1 **Cybersecurity and Ransomware Incidents:** Any clause attempting to classify a ransomware attack, distributed denial-of-service (DDoS) attack, or malicious data breach as a Force Majeure Event. **Escalate to:** Chief Information Security Officer (CISO), Marcus Vance.

14.5.2 **SaaS Availability Service Level Agreement (SLA) Override:** Any clause that permits the counterparty to suspend minimum uptime commitments or waive financial service credits due to a weather or utility event that lasts fewer than seventy-two (72) continuous hours. **Escalate to:** Chief Technology Officer (CTO), Elena Rostova.

14.5.3 **Unilateral Fee Abatement Extension:** Any clause requiring Northwind to pro-rate, refund, or abate subscription fees for a period exceeding ninety (90) days post-resolution of the Force Majeure Event. **Escalate to:** Chief Financial Officer (CFO), David Sterling.

---

### 14.6 Worked Examples of Counterparty Language

#### 14.6.1 Acceptable Counterparty Language (Approved without Escalation)

* **Example A (Acceptable - Extended Notice & Standard Definition):**
  > *"Neither party shall be in default for any failure to perform its obligations under this Agreement if such failure results from any cause beyond its reasonable control, including acts of God, war, terrorism, fire, or public utility failures, provided that the affected party gives written notice within five (5) business days of the occurrence. If such condition continues for more than forty-five (45) days, either party may terminate this Agreement upon written notice."*
  > *Analysis:* While the notice period (5 days) and termination threshold (45 days) diverge from Northwind’s preferred terms, they fall squarely within authorized fallback parameters without introducing economic or labor-related loopholes.

* **Example B (Acceptable - Specific Utility Clarification):**
  > *"Performance shall be excused under this Section only during the continuation of an unforeseeable natural disaster, regional grid failure lasting in excess of twenty-four (24) hours, or government-mandated quarantine, provided the claiming party notifies the other party within three (3) business days and uses diligent efforts to resume performance."*
  > *Analysis:* This narrows the scope favorably toward Northwind, matches the 3-day notice requirement, and properly conditions relief on diligent mitigation efforts.

#### 14.6.2 Unacceptable Counterparty Language (Rejected / Requires Escalation)

* **Example C (Unacceptable - Economic Hardship & Low Threshold):**
  > *"Force Majeure shall include any unforeseeable event, including significant market shifts, inflation exceeding 5% annually, raw material shortages, or labor disruptions, which renders performance commercially impracticable. Performance may be suspended indefinitely until commercial viability is restored, and customer payment obligations are immediately suspended upon notice."*
  > *Analysis:* **Violates walk-away rule 14.3.1(a) and (d).** Introduces economic volatility, eliminates payment obligations, and removes fixed termination timelines. Immediate rejection required.

* **Example D (Unacceptable - Unilateral Control & Extended Suspension):**
  > *"An Affected Party may declare a Force Majeure Event due to internal software bugs, third-party cloud infrastructure degradation, or staffing shortages. Obligations are suspended for up to one hundred eighty (180) days without penalty, and the Customer shall retain all prepaid fees without offset."*
  > *Analysis:* **Violates walk-away rules 14.3.1(b) and triggers CISO/CTO escalation paths.** Normal cloud infrastructure dependencies and internal software bugs are operational risks, not Force Majeure events; a 180-day suspension is commercially fatal.
