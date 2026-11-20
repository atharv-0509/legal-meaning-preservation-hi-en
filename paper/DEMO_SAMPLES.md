# Demo samples: provisions the model has never seen

Each original is the verbatim text of a provision from our official sources (Consumer Protection Act 2019, Gazette
of India; RTI Act 2005, DoPT English and Hindi). None of them appears in any training, dev or test file or in any
augmentation pair; CPA 69(1) appears only in the identical-pair sanity holdout, which is never trained on. The
simplifications were written for this demo, one legal change each, and are not part of the dataset or any result.
Expected outputs were measured on 20 Nov 2026 with the MuRIL demo models (`modeling/checkpoints/muril/demo_model`,
`modeling/checkpoints/errcls/errcls_muril-base-cased-aug`). Paste the original on the left, a simplification on the
right, press **Score**.

## At a glance

| Provision | Faithful | Broken version | Score | Error type shown |
|---|---|---|---|---|
| CPA 69(1) | 10.0 | 2 → 5 years | 4.8 | number / time limit (92%) |
|  |  | reversed | 4.4 | negation (97%) |
| RTI 19(6), Hindi | 10.0 | 30 → 90 days | 4.8 | number / time limit (92%) |
| RTI 19(5) | 9.5 | "does not have to prove" | 3.1 | negation (97%) |
|  |  | burden moved to applicant (missed) | 9.4 | negation (97%) |
| CPA 81(1) (backup) | 9.6 | 7 → 30 days | 4.8 | number / time limit (92%) |
|  |  | shall → may (missed) | 9.6 | obligation ↔ permission (90%) |

What to say: on text it has never seen, the model catches changed numbers (English and Hindi) and reversed meanings
(English), and the error classifier names them. It misses changes in *who* must act or prove something and *shall → may* flips; the classifier
usually still raises a flag. That matches the paper's error analysis.

## 1. Consumer Protection Act 2019, s. 69(1): two-year limit for complaints (English)

**Original**

```
The District Commission, the State Commission or the National Commission shall not admit a complaint unless it is filed within two years from the date on which the cause of action has arisen.
```

**Faithful simplification**  
Expected: **10.0** (Preserved), error type: no error (88%)

```
A district, state or national consumer commission will not accept a complaint unless it is filed within two years from the day the problem arose.
```

**Broken: two years → five years**  
Expected: **4.8** (Partially Preserved), error type: number / time limit (92%)

```
A district, state or national consumer commission will not accept a complaint unless it is filed within five years from the day the problem arose.
```

**Broken: "will not accept … unless" → "will accept … even if"**  
Expected: **4.4** (Partially Preserved), error type: negation (97%)

```
A district, state or national consumer commission will accept a complaint even if it is filed more than two years after the problem arose.
```

## 2. RTI Act 2005, s. 19(6): deadline for deciding an appeal (Hindi)

**Original**

```
उपधारा (1) या उपधारा (2) के अधीन किसी अपील का निपटारा, लेखबद्ध किए जाने वाले कारणों से, अपील की प्राप्ति के तीस दिन के भीतर या ऐसी विस्तारित अवधि के भीतर, जो उसके फाइल किए जाने की तारीख से कुल पैंतालीस दिन से अधिक न हो, किया जाएगा।
```

**Faithful simplification**  
Expected: **10.0** (Preserved), error type: no error (88%)

```
उपधारा (1) या उपधारा (2) के अधीन किसी अपील का निपटारा अपील मिलने के तीस दिन के भीतर, या फाइल करने की तारीख से कुल पैंतालीस दिन से अधिक न होने वाली बढ़ी हुई अवधि के भीतर, कारण लिखकर, किया जाएगा।
```

**Broken: तीस दिन (30 days) → नब्बे दिन (90 days)**  
Expected: **4.8** (Partially Preserved), error type: number / time limit (92%)

```
उपधारा (1) या उपधारा (2) के अधीन किसी अपील का निपटारा अपील मिलने के नब्बे दिन के भीतर, या फाइल करने की तारीख से कुल पैंतालीस दिन से अधिक न होने वाली बढ़ी हुई अवधि के भीतर, कारण लिखकर, किया जाएगा।
```

## 3. RTI Act 2005, s. 19(5): who must prove a refusal was justified (English)

**Original**

```
In any appeal proceedings, the onus to prove that a denial of a request was justified shall be on the Central Public Information Officer or State Public Information Officer, as the case may be, who denied the request.
```

**Faithful simplification**  
Expected: **9.5** (Preserved), error type: no error (88%)

```
In an appeal, the Public Information Officer who refused a request must prove that the refusal was justified.
```

**Broken: "must prove" → "does not have to prove"**  
Expected: **3.1** (Partially Preserved), error type: negation (97%)

```
In an appeal, the Public Information Officer who refused a request does not have to prove that the refusal was justified.
```

**Broken: the burden moves from the officer to the applicant. **Honest failure**: the score misses it (9.4); the classifier flags "negation" only because of the word "not". Shifting a burden of proof is not one of the five error types we trained on.**  
Expected: **9.4** (Preserved), error type: negation (97%)

```
In an appeal, the person whose request was refused must prove that the refusal was not justified.
```

## Backup: Consumer Protection Act 2019, s. 81(1): seven days to record a mediated settlement

**Original**

```
The District Commission or the State Commission or the National Commission, as the case may be, shall, within seven days of the receipt of the settlement report, pass suitable order recording such settlement of consumer dispute and dispose of the matter accordingly.
```

**Faithful simplification**  
Expected: **9.6** (Preserved), error type: no error (88%)

```
Within seven days of receiving the settlement report, the District, State or National Commission shall pass an order recording the settlement and close the case.
```

**Broken: seven days → thirty days**  
Expected: **4.8** (Partially Preserved), error type: number / time limit (92%)

```
Within thirty days of receiving the settlement report, the District, State or National Commission shall pass an order recording the settlement and close the case.
```

**Broken: "shall pass an order" → "may pass an order" (missed by the score, named by the classifier)**  
Expected: **9.6** (Preserved), error type: obligation ↔ permission (90%)

```
Within seven days of receiving the settlement report, the District, State or National Commission may pass an order recording the settlement and close the case.
```

## Backup: RTI Act 2005, s. 19(6) in English

**Original**

```
An appeal under sub-section (1) or sub-section (2) shall be disposed of within thirty days of the receipt of the appeal or within such extended period not exceeding a total of forty-five days from the date of filing thereof, as the case may be, for reasons to be recorded in writing.
```

**Faithful simplification**  
Expected: **8.5** (Preserved), error type: no error (88%)

```
An appeal under sub-section (1) or (2) shall be decided within thirty days of receiving it, or within a longer period of at most forty-five days in total from the date it was filed, with the reasons for the delay recorded in writing.
```

**Broken: thirty → ninety days**  
Expected: **4.9** (Partially Preserved), error type: number / time limit (92%)

```
An appeal under sub-section (1) or (2) shall be decided within ninety days of receiving it, or within a longer period of at most forty-five days in total from the date it was filed, with the reasons for the delay recorded in writing.
```

**Broken: the 45-day extension and the written reasons are dropped**  
Expected: **5.2** (Partially Preserved), error type: exception dropped (87%)

```
An appeal under sub-section (1) or (2) shall be decided within thirty days of receiving it.
```

**Broken: "shall be decided" → "may be decided" (missed by the score, named by the classifier)**  
Expected: **8.0** (Preserved), error type: obligation ↔ permission (90%)

```
An appeal under sub-section (1) or (2) may be decided within thirty days of receiving it, or within a longer period of at most forty-five days in total from the date it was filed, with the reasons for the delay recorded in writing.
```

## Do not use live

- RTI 19(6) in Hindi with a negation ("… नहीं किया जाएगा") scores 9.2: a Hindi reversal the score misses (the
  classifier still says negation, 96%). Use it only if asked about Hindi weaknesses.
- CPA 89 and RTI 8(2) (English) appear in the demo model's training data as augmentation pairs, so they do not
  count as unseen.
