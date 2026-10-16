# Playbook: Intellectual Property Ownership

# NORTHWIND SYSTEMS INTERNAL LEGAL PLAYBOOK
## SECTION 4: INTELLECTUAL PROPERTY OWNERSHIP

### 4.1 Preferred Position (Model Clause Language)

The following clause represents the standard Northwind Systems position and must be inserted into all inbound and outbound enterprise SaaS agreements without modification, subject only to the escalation thresholds defined in Section 4.5.

> **4.1.1 Northwind Intellectual Property.** Northwind exclusively owns and retains all right, title, and interest in and to the Service, the Underlying Technology, Documentation, and all improvements, enhancements, modifications, and derivative works thereof, including all related intellectual property rights. Except for the express licenses granted herein, no intellectual property rights are granted to Customer under this Agreement by implication, estoppel, or otherwise.
>
> **4.1.2 Customer Data.** Customer exclusively owns all right, title, and interest in and to all Customer Data. Customer grants Northwind a worldwide, non-exclusive, royalty-free, fully paid-up license to host, copy, process, display, and use Customer Data solely as necessary to provide, maintain, and support the Service for Customer during the Term.
>
> **4.1.3 Feedback.** If Customer or its users provide any suggestions, enhancement requests, recommendations, or other feedback regarding the Service ("Feedback"), Northwind may freely use, disclose, reproduce, license, and otherwise distribute and exploit such Feedback as part of its products and services, without obligation or restriction of any kind on account of intellectual property rights or otherwise.
>
> **4.1.4 Aggregated Statistics.** Notwithstanding anything to the contrary herein, Northwind may monitor Customer’s use of the Service and collect, compile, and analyze data and information relating to the provision, use, and performance of various aspects of the Service and related systems ("Aggregated Statistics"). Northwind may (a) freely make and use Aggregated Statistics for diagnosis, correction, maintenance, product improvement, and development purposes, and (b) freely disclose Aggregated Statistics in non-identifiable, anonymized form in connection with its business.

---

### 4.2 Fallback Position

If the counterparty rejects the Preferred Position regarding Customer Data ownership or requests joint ownership of derivative works or custom developments, legal counsel may deploy the following fallback positions sequentially.

*   **Fallback 4.2.1 (Customer-Specific Configurations):** If Customer mandates ownership of custom configurations, reports, or integrations built specifically for them by Northwind, permit Customer to own the specific output configuration *provided that* Customer grants Northwind an irrevocable, perpetual, royalty-free, transferable license to use such configurations as part of the Underlying Technology, and Customer pays an upfront professional services fee of not less than $50,000 for the development work.
*   **Fallback 4.2.2 (Feedback Restriction):** If Customer objects to unrestricted Feedback rights, limit Northwind’s use to "internal product improvement and analytics" and explicitly prohibit the public attribution of Feedback to Customer without prior written consent.
*   **Fallback 4.2.3 (Data Portability SLA):** In exchange for maintaining standard IP ownership under Section 4.1, Northwind may agree to a strict data extraction obligation: Northwind shall make all Customer Data available for retrieval in a structured, industry-standard comma-separated values (CSV) or JSON format within exactly fourteen (14) calendar days following the effective date of termination, after which Northwind shall permanently purge all Customer Data within ninety (90) calendar days.

---

### 4.3 Walk-Away Position

Legal counsel and sales representatives must immediately cease negotiations and escalate to the Chief Executive Officer if the counterparty insists upon any of the following terms, as they present unacceptable enterprise risk to Northwind Systems:

1.  **Transfer of Core IP:** Any demand that Customer shall own any right, title, or interest in or to the Northwind multi-tenant SaaS platform, core application code, underlying database architecture, or proprietary algorithms.
2.  **Perpetual Exclusive License to Core Tech:** Any demand for an exclusive, perpetual, irrevocable, source-code-level license to the Service.
3.  **Uncapped Indemnity for IP Infringement:** Any refusal to cap Northwind’s intellectual property indemnification liability at the monetary limits defined in Section 4.4.1.
4.  **Open Source Contamination:** Any requirement that Northwind incorporate third-party open-source software under terms that would compel Northwind to license its proprietary source code under a GNU General Public License (GPL) or similar copyleft regime.

---

### 4.4 Specific Thresholds and Metrics

The following quantitative limits, notice periods, cure intervals, and monetary figures govern all IP negotiations and must not be exceeded without written authorization.

*   **4.4.1 IP Indemnification Cap:** Northwind’s maximum aggregate liability for third-party intellectual property infringement claims arising out of the Service shall be capped at exactly **two times (2x)** the total annual recurring revenue (ARR) actually paid by Customer to Northwind in the twelve (12) months preceding the claim, subject to an absolute monetary floor of **$250,000** and a ceiling not to exceed **$1,000,000**.
*   **4.4.2 Infringement Defense Notice Period:** Customer must provide written notice of any third-party IP infringement claim to Northwind within **ten (10) business days** of receipt. Failure to provide timely notice shall release Northwind from its indemnification obligations to the extent such failure materially prejudices Northwind’s defense.
*   **4.4.3 Cure Period for IP Breaches:** If either party commits an alleged material breach of intellectual property or confidentiality provisions, the non-breaching party must provide written notice specifying the breach, and the breaching party shall have a strict cure period of **thirty (30) calendar days** from receipt of notice to remedy the breach before terminating the Agreement.
*   **4.4.4 Professional Services IP Floor:** No custom development, integration, or API connector shall be delivered on a "work made for hire" basis unless the Statement of Work (SOW) includes a minimum professional services fee floor of **$75,000**, and the contract explicitly reserves Northwind’s underlying background intellectual property.

---

### 4.5 Named Deviations and Escalation Matrix

Any departure from the Preferred or Fallback positions that touches upon the following structural categories requires formal written approval from the designated corporate officer before contract execution.

| Deviation Category | Description of Non-Standard Term | Required Escalation Authority |
| :--- | :--- | :--- |
| **Custom IP / Work Made For Hire** | Any agreement where Customer acquires ownership of code, algorithms, or application modifications developed by Northwind. | **Chief Technology Officer (CTO)** and **General Counsel** |
| **Unlimited / Uncapped IP Indemnity** | Any counterparty demand for intellectual property indemnification that exceeds the 2x ARR cap or breaches the $1,000,000 ceiling. | **Chief Financial Officer (CFO)** |
| **Source Code Escrow** | Any agreement requiring Northwind to deposit its proprietary source code into a third-party escrow account for Customer's benefit. | **Chief Executive Officer (CEO)** and **CTO** |

---

### 4.6 Worked Examples of Counterparty Language

#### Acceptable Counterparty Language (Approved for Inclusion)

*   **Example A.1 (Data Ownership Clarification):** *"Customer acknowledges that nothing in this Agreement transfers to Customer any right, title, or interest in the Service, and that all intellectual property rights in the platform remain exclusively with Northwind. Customer retains all right, title, and interest in raw Customer Data uploaded to the platform."*
    *   *Analysis:* Acceptable because it explicitly reinforces Northwind’s ownership of the platform while affirming Customer’s baseline ownership of their raw data without creating joint ownership of derivative works.
*   **Example A.2 (Custom Deliverables Provision):** *"In the event Northwind develops custom reporting scripts specifically commissioned and separately paid for by Customer under SOW #4, Customer shall own the copyright in the specific output scripts, subject to a perpetual, non-exclusive license granted to Northwind to use such scripts within the Service."*
    *   *Analysis:* Acceptable because it satisfies Fallback 4.2.1: Customer receives output ownership of discrete custom scripts, but Northwind retains the necessary broad license to incorporate the underlying logic into its platform.

#### Unacceptable Counterparty Language (Prohibited / Must Be Rejected)

*   **Example U.1 (Joint Ownership Claim):** *"All software, documentation, modifications, and intellectual property developed jointly or severally by the parties during the performance of this Agreement, including all custom configurations and workflow templates, shall be jointly owned by Northwind and Customer on an equal 50/50 basis worldwide."*
    *   *Analysis:* Prohibited. Violates Section 4.3 (Walk-Away Position 1) by attempting to seize joint ownership of platform modifications and workflow templates, creating severe commercialization blocks for Northwind.
*   **Example U.2 (Work Made For Hire Overreach):** *"The Service, including all underlying source code, user interfaces, and related modules created by Northwind for use under this Agreement, shall be deemed a 'work made for hire' exclusively owned by Customer ab initio. Northwind hereby assigns all worldwide right, title, and interest therein to Customer."*
    *   *Analysis:* Prohibited. This is an immediate walk-away trigger under Section 4.3. It destroys Northwind’s core multi-tenant SaaS business model by assigning the underlying platform to the Customer.
