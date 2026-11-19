# Error analysis: xlm-roberta-base-da (random)

20 cases; predictions averaged over 3 runs. Fill in **Analysis** by hand.

## Case 1 — injected exception_drop

`rti-s9|hi|perturbed` · gold 4.00 (± 0.00, Partially Preserved) · predicted 7.31 (Preserved) · error type: exception_drop · annotators' main change: tie:condition/exception

**Original:** धारा 8 के उपबन्धों पर प्रतिकूल प्रभाव डाले बिना, यथास्थिति, कोई केन्द्रीय लोक सूचना अधिकारी या कोई राज्य लोक सूचना अधिकारी सूचना के किसी अनुरोध को वहां अस्वीकार कर सकेगा, जहां पहुंच उपलब्ध कराने के लिए ऐसा अनुरोध राज्य से भिन्न किसी व्यक्ति के अस्तित्वयुक्त प्रतिलिप्यधिकार का उल्लंघन अन्तर्वलित करेगा।

**Simplification:** धारा 8 के प्रावधानों पर असर डाले बिना, कोई केन्द्रीय या राज्य लोक सूचना अधिकारी सूचना के अनुरोध को मना कर सकता है,किसी दूसरे व्यक्ति के कॉपीराइट का उल्लंघन होगा।

**Analysis:** [TBD — written by the team]

## Case 2 — injected exception_drop

`rti-s17_4|hi|perturbed` · gold 5.00 (± 0.00, Partially Preserved) · predicted 8.14 (Preserved) · error type: exception_drop · annotators' main change: exception

**Original:** यदि राज्य मुख्य सूचना आयुक्त या कोई राज्य सूचना आयुक्त, किसी प्रकार, राज्य सरकार द्वारा या उसकी ओर से की गई किसी संविदा या करार से संबद्ध या उसमें हितबद्ध है या किसी निगमित कंपनी के किसी सदस्य को किसी रूप में से अन्यथा और उसके अन्य सदस्यों के साथ सामान्यतः उसके लाभ में या उससे प्रोद्भूत होने वाले किसी फायदे या परिलब्धियों में हिस्सा लेता है तो वह उपधारा (1) के प्रयोजनों के लिए कदाचार का दोषी समझा जाएगा।

**Simplification:** अगर राज्य मुख्य सूचना आयुक्त या कोई राज्य सूचना आयुक्त राज्य सरकार द्वारा या उसकी ओर से किए गए किसी अनुबंध या करार से किसी तरह जुड़ा है या उसमें उसका हित है,किसी और रूप में उसके लाभ या फ़ायदे में हिस्सा लेता है, तो उपधारा (1) के लिए उसे कदाचार का दोषी माना जाएगा।

**Analysis:** [TBD — written by the team]

## Case 3 — injected modality

`cpa-s58_2|en|perturbed` · gold 5.00 (± 0.00, Partially Preserved) · predicted 9.98 (Preserved) · error type: modality · annotators' main change: obligation/permission

**Original:** The jurisdiction, powers and authority of the National Commission may be exercised by Benches thereof and a Bench may be constituted by the President with one or more members as he may deem fit: Provided that the senior-most member of the Bench shall preside over the Bench.

**Simplification:** The National Commission can use its jurisdiction, powers and authority through its Benches. The President must form a Bench with one or more members as he thinks fit, and the most senior member of the Bench will lead it.

**Analysis:** [TBD — written by the team]

## Case 4 — injected modality

`rti-s17_2|en|perturbed` · gold 5.00 (± 0.00, Partially Preserved) · predicted 9.89 (Preserved) · error type: modality · annotators' main change: obligation/permission

**Original:** The Governor may suspend from office, and if deem necessary prohibit also from attending the office during inquiry, the State Chief Information Commissioner or a State Information Commissioner in respect of whom a reference has been made to the Supreme Court under sub-section (1) until the Governor has passed orders on receipt of the report of the Supreme Court on such reference.

**Simplification:** The Governor must suspend a State Chief Information Commissioner or State Information Commissioner whose case has been sent to the Supreme Court under sub-section (1). If needed, the Governor may also stop them from coming to the office during the inquiry. This lasts until the Governor passes orders after receiving the Supreme Court's report.

**Analysis:** [TBD — written by the team]

## Case 5 — injected negation

`rti-s17_2|hi|perturbed` · gold 3.00 (± 2.00, Partially Preserved) · predicted 9.64 (Preserved) · error type: negation · annotators' main change: negation

**Original:** राज्यपाल, उस राज्य मुख्य सूचना आयुक्त या राज्य सूचना आयुक्त को, जिसके विरुद्ध उपधारा (1) के अधीन उच्चतम न्यायालय को निर्देश किया गया है, ऐसे निर्देश पर उच्चतम न्यायालय की रिपोर्ट की प्राप्ति पर राज्यपाल द्वारा आदेश पारित किए जाने तक, पद से निलंबित कर सकेगा और यदि आवश्यक समझे तो ऐसी जांच के दौरान कार्यालय में उपस्थित होने से प्रतिषिद्ध भी कर सकेगा।

**Simplification:** जिस राज्य मुख्य सूचना आयुक्त या राज्य सूचना आयुक्त के ख़िलाफ़ उपधारा (1) के तहत उच्चतम न्यायालय को मामला भेजा गया है, राज्यपाल उसे पद से निलंबित नहीं कर सकते हैं। ज़रूरी लगे तो वे जाँच के दौरान उसे दफ़्तर आने से भी रोक सकते हैं। यह तब तक चलेगा जब तक राज्यपाल उच्चतम न्यायालय की रिपोर्ट मिलने पर आदेश न दे दें।

**Analysis:** [TBD — written by the team]

## Case 6 — injected negation

`cpa-s3_1|en|perturbed` · gold 2.50 (± 1.50, Partially Preserved) · predicted 8.43 (Preserved) · error type: negation · annotators' main change: negation

**Original:** The Central Government shall, by notification, establish with effect from such date as it may specify in that notification, the Central Consumer Protection Council to be known as the Central Council.

**Simplification:** The Central Government will not set up the Central Consumer Protection Council, called the Central Council, by a notification, starting from the date given in that notification.

**Analysis:** [TBD — written by the team]

## Case 7 — injected number

`rti-s19_3|hi|perturbed` · gold 4.50 (± 0.50, Partially Preserved) · predicted 8.36 (Preserved) · error type: number · annotators' main change: date/time limit

**Original:** उपधारा (1) के अधीन विनिश्चय के विरुद्ध दूसरी अपील उस तारीख से, जिसको विनिश्चय किया जाना चाहिए था या वास्तव में प्राप्त किया गया था, नब्बे दिन के भीतर केन्द्रीय सूचना आयोग या राज्य सूचना आयोग को होगी : परन्तु, यथास्थिति, केन्द्रीय सूचना आयोग या राज्य सूचना आयोग नब्बे दिन की अवधि की समाप्ति के पश्चात् अपील को ग्रहण कर सकेगा, यदि उसका यह समाधान हो जाता है कि अपीलार्थी समय पर अपील फाइल करने से पर्याप्त कारण से निवारित किया गया था।

**Simplification:** उपधारा (1) के तहत हुए फ़ैसले के ख़िलाफ़ दूसरी अपील केन्द्रीय सूचना आयोग या राज्य सूचना आयोग में की जा सकती है। यह अपील उस तारीख से 120 दिन के भीतर करनी होगी, जिस दिन फ़ैसला होना चाहिए था या असल में मिला था। लेकिन अगर आयोग को लगे कि अपील करने वाले के पास देरी का सही कारण था, तो वह नब्बे दिन के बाद भी अपील स्वीकार कर सकता है।

**Analysis:** [TBD — written by the team]

## Case 8 — injected number

`rti-s19_3|en|perturbed` · gold 5.00 (± 0.00, Partially Preserved) · predicted 8.51 (Preserved) · error type: number · annotators' main change: tie:date/time limit/number/amount

**Original:** A second appeal against the decision under sub-section (1) shall lie within ninety days from the date on which the decision should have been made or was actually received, with the Central Information Commission or the State Information Commission: Provided that the Central Information Commission or the State Information Commission, as the case may be, may admit the appeal after the expiry of the period of ninety days if it is satisfied that the appellant was prevented by sufficient cause from filing the appeal in time.

**Simplification:** A second appeal against a decision under sub-section (1) can be filed with the Central Information Commission or the State Information Commission within ninety days from the date the decision should have been made or was actually received. However, the Commission may accept the appeal after 120 days if it is satisfied that the appellant had a good reason for not filing it on time.

**Analysis:** [TBD — written by the team]

## Case 9 — injected scope

`rti-s4_2|en|perturbed` · gold 5.00 (± 0.00, Partially Preserved) · predicted 9.27 (Preserved) · error type: scope · annotators' main change: scope

**Original:** It shall be a constant endeavour of every public authority to take steps in accordance with the requirements of clause (b) of sub-section (1) to provide as much information suomotu to the public at regular intervals through various means of communications, including internet, so that the public have minimum resort to the use of this Act to obtain information.

**Simplification:** Some public authority must keep trying, as required by clause (b) of sub-section (1), to share as much information as possible with the public on its own, at regular intervals and through different means of communication, including the internet. This way, people will rarely need to use this Act to get information.

**Analysis:** [TBD — written by the team]

## Case 10 — injected scope

`rti-s25_1|en|perturbed` · gold 5.00 (± 0.00, Partially Preserved) · predicted 8.47 (Preserved) · error type: scope · annotators' main change: scope

**Original:** The Central Information Commission or State Information Commission, as the case may be, shall, as soon as practicable after the end of each year, prepare a report on the implementation of the provisions of this Act during that year and forward a copy thereof to the appropriate Government.

**Simplification:** As soon as possible after the end of some year, the Central or State Information Commission must prepare a report on how the provisions of this Act were carried out during that year and send a copy to the appropriate Government.

**Analysis:** [TBD — written by the team]

## Case 11 — annotators: condition

`cpa-s38_1|en|perturbed` · gold 5.00 (± 0.00, Partially Preserved) · predicted 7.12 (Preserved) · error type: negation · annotators' main change: condition

**Original:** The District Commission shall, on admission of a complaint, or in respect of cases referred for mediation on failure of settlement by mediation, proceed with such complaint.

**Simplification:** After admitting a complaint, or when a case sent for mediation has been settled, the District Commission will go ahead with the complaint.

**Analysis:** [TBD — written by the team]

## Case 12 — annotators: number/amount

`cpa-s34_1|en|perturbed` · gold 5.00 (± 0.00, Partially Preserved) · predicted 7.99 (Preserved) · error type: number · annotators' main change: number/amount

**Original:** Subject to the other provisions of this Act, the District Commission shall have jurisdiction to entertain complaints where the value of the goods or services paid as consideration does not exceed one crore rupees: Provided that where the Central Government deems it necessary so to do, it may prescribe such other value, as it deems fit.

**Simplification:** Subject to the other provisions of this Act, the District Commission can hear complaints where the value of the goods or services paid for is not more than two crore rupees. However, the Central Government may set a different value if it thinks it is necessary.

**Analysis:** [TBD — written by the team]

## Case 13 — annotators: omission

`rti-s9|en|aggressive` · gold 6.00 (± 2.00, Partially Preserved) · predicted 9.09 (Preserved) · error type: — · annotators' main change: omission

**Original:** Without prejudice to the provisions of section 8, a Central Public Information Officer or a State Public Information Officer, as the case may be, may reject a request for information where such a request for providing access would involve an infringement of copyright subsisting in a person other than the State.

**Simplification:** An information officer can say no to a request if sharing the information would break someone's copyright.

**Analysis:** [TBD — written by the team]

## Case 14 — annotators: tie:condition/none

`rti-s15_7|en|perturbed` · gold 9.00 (± 1.00, Preserved) · predicted 7.04 (Preserved) · error type: scope · annotators' main change: tie:condition/none

**Original:** The headquarters of the State Information Commission shall be at such place in the State as the State Government may, by notification in the Official Gazette, specify and the State Information Commission may, with the previous approval of the State Government, establish offices at other places in the State.

**Simplification:** The State Government will choose the place in the State where the State Information Commission has its main office, and will announce it in the Official Gazette. The Commission may also open offices in other places in the State, but if the State Government agrees first.

**Analysis:** [TBD — written by the team]

## Case 15 — annotators: tie:condition/omission

`cpa-s51_4|en|aggressive` · gold 6.50 (± 2.50, Partially Preserved) · predicted 7.39 (Preserved) · error type: — · annotators' main change: tie:condition/omission

**Original:** Where the National Commission is satisfied that a substantial question of law is involved in any case, it shall formulate that question and hear the appeal on that question: Provided that nothing in this sub-section shall be deemed to take away or abridge the power of the National Commission to hear, for reasons to be recorded in writing, the appeal on any other substantial question of law, if it is satisfied that the case involves such question of law.

**Simplification:** The National Commission writes down the main legal question in a case and hears the appeal on it. It can also look at other important legal questions if it explains why.

**Analysis:** [TBD — written by the team]

## Case 16 — annotators: tie:date/time limit/omission

`rti-s19_3|hi|aggressive` · gold 9.00 (± 0.00, Preserved) · predicted 6.04 (Partially Preserved) · error type: — · annotators' main change: tie:date/time limit/omission

**Original:** उपधारा (1) के अधीन विनिश्चय के विरुद्ध दूसरी अपील उस तारीख से, जिसको विनिश्चय किया जाना चाहिए था या वास्तव में प्राप्त किया गया था, नब्बे दिन के भीतर केन्द्रीय सूचना आयोग या राज्य सूचना आयोग को होगी : परन्तु, यथास्थिति, केन्द्रीय सूचना आयोग या राज्य सूचना आयोग नब्बे दिन की अवधि की समाप्ति के पश्चात् अपील को ग्रहण कर सकेगा, यदि उसका यह समाधान हो जाता है कि अपीलार्थी समय पर अपील फाइल करने से पर्याप्त कारण से निवारित किया गया था।

**Simplification:** पहली अपील से संतुष्ट न हों तो 90 दिन के अंदर सूचना आयोग में दूसरी अपील कर सकते हैं। देर होने पर भी सही कारण हो तो आयोग अपील सुन सकता है।

**Analysis:** [TBD — written by the team]

## Case 17 — annotators: tie:exception/omission

`rti-s9|en|perturbed` · gold 7.00 (± 2.00, Preserved) · predicted 9.73 (Preserved) · error type: exception_drop · annotators' main change: tie:exception/omission

**Original:** Without prejudice to the provisions of section 8, a Central Public Information Officer or a State Public Information Officer, as the case may be, may reject a request for information where such a request for providing access would involve an infringement of copyright subsisting in a person other than the State.

**Simplification:** Without affecting section 8, a Central or State Public Information Officer may refuse a request for information if giving access would break the copyright of a person.

**Analysis:** [TBD — written by the team]

## Case 18 — annotators: tie:none/obligation/permission

`rti-s14_1|hi|normal` · gold 9.50 (± 0.50, Preserved) · predicted 7.21 (Preserved) · error type: — · annotators' main change: tie:none/obligation/permission

**Original:** उपधारा (3) के उपबंधों के अधीन रहते हुए, मुख्य सूचना आयुक्त या किसी सूचना आयुक्त को राष्ट्रपति के आदेश द्वारा साबित कदाचार या असमर्थता के आधार पर उसके पद से तभी हटाया जाएगा, जब उच्चतम न्यायालय ने, राष्ट्रपति द्वारा उसे किए गए किसी निर्देश पर जांच के पश्चात् यह रिपोर्ट दी हो कि, यथास्थिति, मुख्य सूचना आयुक्त या सूचना आयुक्त को उस आधार पर हटा दिया जाना चाहिए।

**Simplification:** उपधारा (3) के प्रावधानों के अधीन, मुख्य सूचना आयुक्त या किसी सूचना आयुक्त को साबित कदाचार या असमर्थता के आधार पर केवल राष्ट्रपति के आदेश से पद से हटाया जा सकेगा। ऐसा तभी होगा जब राष्ट्रपति मामला उच्चतम न्यायालय को भेजें और उच्चतम न्यायालय जाँच के बाद यह रिपोर्ट दे कि उसे उस आधार पर हटाया जाना चाहिए।

**Analysis:** [TBD — written by the team]

## Case 19 — annotators: tie:none/omission

`cpa-s36_2|en|aggressive` · gold 9.50 (± 0.50, Preserved) · predicted 6.21 (Partially Preserved) · error type: — · annotators' main change: tie:none/omission

**Original:** On receipt of a complaint made under section 35, the District Commission may, by order, admit the complaint for being proceeded with or reject the same: Provided that a complaint shall not be rejected under this section unless an opportunity of being heard has been given to the complainant: Provided further that the admissibility of the complaint shall ordinarily be decided within twenty-one days from the date on which the complaint was filed.

**Simplification:** When you file a consumer complaint, the District Commission decides whether to take it up, usually within 21 days. It has to listen to you before saying no.

**Analysis:** [TBD — written by the team]

## Case 20 — annotators: tie:none/other

`rti-s4_2|hi|perturbed` · gold 9.50 (± 0.50, Preserved) · predicted 9.79 (Preserved) · error type: modality · annotators' main change: tie:none/other

**Original:** प्रत्येक लोक अधिकारी का निरंतर यह प्रयास होगा कि वह उपधारा (1) के खंड (ख) की अपेक्षाओं के अनुसार, स्वप्रेरणा से, जनता को नियमित अन्तरालों पर संसूचना के विभिन्न साधनों के माध्यम से, जिनके अन्तर्गत इंटरनेट भी है, इतनी अधिक सूचना उपलब्ध कराने के लिए उपाय करे जिससे कि जनता को सूचना प्राप्त करने के लिए इस अधिनियम का कम से कम अवलंब लेना पड़े।

**Simplification:** हर लोक प्राधिकारी लगातार यह कोशिश करेगा कि उपधारा (1) के खंड (ख) के अनुसार वह खुद ही, नियमित अंतराल पर, इंटरनेट सहित संचार के अलग-अलग साधनों से जनता को ज़्यादा से ज़्यादा सूचना दे। इससे लोगों को सूचना पाने के लिए इस अधिनियम का कम से कम सहारा लेना पड़ सकेगा।

**Analysis:** [TBD — written by the team]
