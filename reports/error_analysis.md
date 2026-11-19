# Error analysis: xlm-roberta-base-frjudge (random)

20 cases; predictions averaged over 3 runs. Fill in **Analysis** by hand.

## Case 1 — injected exception_drop

`rti-s6_2|en|perturbed` · gold 5.00 (± 0.00, Partially Preserved) · predicted 8.87 (Preserved) · error type: exception_drop · annotators' main change: exception

**Original:** An applicant making request for information shall not be required to give any reason for requesting the information or any other personal details except those that may be necessary for contacting him.

**Simplification:** A person asking for information does not have to give any reason for the request. They also do not have to give any personal details.

**Analysis:** [TBD — written by the team]

## Case 2 — injected exception_drop

`rti-s9|hi|perturbed` · gold 4.00 (± 0.00, Partially Preserved) · predicted 7.70 (Preserved) · error type: exception_drop · annotators' main change: tie:condition/exception

**Original:** धारा 8 के उपबन्धों पर प्रतिकूल प्रभाव डाले बिना, यथास्थिति, कोई केन्द्रीय लोक सूचना अधिकारी या कोई राज्य लोक सूचना अधिकारी सूचना के किसी अनुरोध को वहां अस्वीकार कर सकेगा, जहां पहुंच उपलब्ध कराने के लिए ऐसा अनुरोध राज्य से भिन्न किसी व्यक्ति के अस्तित्वयुक्त प्रतिलिप्यधिकार का उल्लंघन अन्तर्वलित करेगा।

**Simplification:** धारा 8 के प्रावधानों पर असर डाले बिना, कोई केन्द्रीय या राज्य लोक सूचना अधिकारी सूचना के अनुरोध को मना कर सकता है,किसी दूसरे व्यक्ति के कॉपीराइट का उल्लंघन होगा।

**Analysis:** [TBD — written by the team]

## Case 3 — injected modality

`rti-s12_1|hi|perturbed` · gold 5.00 (± 0.00, Partially Preserved) · predicted 9.78 (Preserved) · error type: modality · annotators' main change: obligation/permission

**Original:** केन्द्रीय सरकार, राजपत्र में अधिसूचना द्वारा, केन्द्रीय सूचना आयोग के नाम से ज्ञात एक निकाय का गठन करेगी, जो ऐसी शक्तियों का प्रयोग और ऐसे कृत्यों का पालन करेगा, जो उसे इस अधिनियम के अधीन सौंपे जाएं।

**Simplification:** केन्द्रीय सरकार राजपत्र में अधिसूचना जारी करके केन्द्रीय सूचना आयोग नाम का एक निकाय बनाएगी। यह आयोग इस अधिनियम के तहत दी गई शक्तियों का इस्तेमाल करेगा और सौंपे गए काम कर सकेगा।

**Analysis:** [TBD — written by the team]

## Case 4 — injected modality

`rti-s24_3|hi|perturbed` · gold 5.00 (± 0.00, Partially Preserved) · predicted 9.62 (Preserved) · error type: modality · annotators' main change: obligation/permission

**Original:** उपधारा (2) के अधीन जारी की गई प्रत्येक अधिसूचना, संसद् के प्रत्येक सदन के समक्ष रखी जाएगी।

**Simplification:** उपधारा (2) के तहत जारी हर अधिसूचना को संसद के दोनों सदनों के सामने रखा जा सकेगा।

**Analysis:** [TBD — written by the team]

## Case 5 — injected negation

`rti-s14_1|hi|perturbed` · gold 2.50 (± 1.50, Partially Preserved) · predicted 9.66 (Preserved) · error type: negation · annotators' main change: negation

**Original:** उपधारा (3) के उपबंधों के अधीन रहते हुए, मुख्य सूचना आयुक्त या किसी सूचना आयुक्त को राष्ट्रपति के आदेश द्वारा साबित कदाचार या असमर्थता के आधार पर उसके पद से तभी हटाया जाएगा, जब उच्चतम न्यायालय ने, राष्ट्रपति द्वारा उसे किए गए किसी निर्देश पर जांच के पश्चात् यह रिपोर्ट दी हो कि, यथास्थिति, मुख्य सूचना आयुक्त या सूचना आयुक्त को उस आधार पर हटा दिया जाना चाहिए।

**Simplification:** उपधारा (3) के प्रावधानों के अधीन, मुख्य सूचना आयुक्त या किसी सूचना आयुक्त को साबित कदाचार या असमर्थता के आधार पर केवल राष्ट्रपति के आदेश से पद से नहीं हटाया जा सकेगा। ऐसा तभी होगा जब राष्ट्रपति मामला उच्चतम न्यायालय को भेजें और उच्चतम न्यायालय जाँच के बाद यह रिपोर्ट दे कि उसे उस आधार पर हटाया जाना चाहिए।

**Analysis:** [TBD — written by the team]

## Case 6 — injected negation

`cpa-s38_1|en|perturbed` · gold 5.00 (± 0.00, Partially Preserved) · predicted 9.42 (Preserved) · error type: negation · annotators' main change: condition

**Original:** The District Commission shall, on admission of a complaint, or in respect of cases referred for mediation on failure of settlement by mediation, proceed with such complaint.

**Simplification:** After admitting a complaint, or when a case sent for mediation has been settled, the District Commission will go ahead with the complaint.

**Analysis:** [TBD — written by the team]

## Case 7 — injected number

`cpa-s34_1|en|perturbed` · gold 5.00 (± 0.00, Partially Preserved) · predicted 9.62 (Preserved) · error type: number · annotators' main change: number/amount

**Original:** Subject to the other provisions of this Act, the District Commission shall have jurisdiction to entertain complaints where the value of the goods or services paid as consideration does not exceed one crore rupees: Provided that where the Central Government deems it necessary so to do, it may prescribe such other value, as it deems fit.

**Simplification:** Subject to the other provisions of this Act, the District Commission can hear complaints where the value of the goods or services paid for is not more than two crore rupees. However, the Central Government may set a different value if it thinks it is necessary.

**Analysis:** [TBD — written by the team]

## Case 8 — injected number

`cpa-s36_2|en|perturbed` · gold 5.00 (± 0.00, Partially Preserved) · predicted 9.05 (Preserved) · error type: number · annotators' main change: date/time limit

**Original:** On receipt of a complaint made under section 35, the District Commission may, by order, admit the complaint for being proceeded with or reject the same: Provided that a complaint shall not be rejected under this section unless an opportunity of being heard has been given to the complainant: Provided further that the admissibility of the complaint shall ordinarily be decided within twenty-one days from the date on which the complaint was filed.

**Simplification:** When the District Commission receives a complaint under section 35, it may accept the complaint so that it can go ahead, or reject it. However, a complaint cannot be rejected unless the complainant has been given a chance to be heard. Also, the decision on whether to accept the complaint should usually be made within fourteen days from the date it was filed.

**Analysis:** [TBD — written by the team]

## Case 9 — injected scope

`rti-s12_4|hi|perturbed` · gold 5.00 (± 0.00, Partially Preserved) · predicted 9.05 (Preserved) · error type: scope · annotators' main change: scope

**Original:** केन्द्रीय सूचना आयोग के कार्यों का साधारण अधीक्षण, निदेशन और प्रबंधन, मुख्य सूचना आयुक्त में निहित होगा, जिसकी सहायता सूचना आयुक्तों द्वारा की जाएगी और वह ऐसी सभी शक्तियों का प्रयोग और ऐसे सभी कार्य और बातें कर सकेगा, जिनका केन्द्रीय सूचना आयोग द्वारा स्वतंत्र रूप से इस अधिनियम के अधीन किसी अन्य प्राधिकारी के निदेशों के अधीन रहे बिना प्रयोग किया जा सकता है या जो की जा सकती है।

**Simplification:** केन्द्रीय सूचना आयोग के कामकाज की देखरेख, निर्देशन और प्रबंधन मुख्य सूचना आयुक्त के पास होगा, और सूचना आयुक्त उसकी मदद करेंगे। मुख्य सूचना आयुक्त आयोग की सभी शक्तियों का इस्तेमाल कर सकेगा और वे कुछ काम कर सकेगा जो आयोग स्वतंत्र रूप से, किसी दूसरे प्राधिकारी के निर्देश के बिना, इस अधिनियम के तहत कर सकता है।

**Analysis:** [TBD — written by the team]

## Case 10 — injected scope

`rti-s4_2|en|perturbed` · gold 5.00 (± 0.00, Partially Preserved) · predicted 8.91 (Preserved) · error type: scope · annotators' main change: scope

**Original:** It shall be a constant endeavour of every public authority to take steps in accordance with the requirements of clause (b) of sub-section (1) to provide as much information suomotu to the public at regular intervals through various means of communications, including internet, so that the public have minimum resort to the use of this Act to obtain information.

**Simplification:** Some public authority must keep trying, as required by clause (b) of sub-section (1), to share as much information as possible with the public on its own, at regular intervals and through different means of communication, including the internet. This way, people will rarely need to use this Act to get information.

**Analysis:** [TBD — written by the team]

## Case 11 — annotators: omission

`rti-s12_4|hi|aggressive` · gold 8.50 (± 0.50, Preserved) · predicted 5.13 (Partially Preserved) · error type: — · annotators' main change: omission

**Original:** केन्द्रीय सूचना आयोग के कार्यों का साधारण अधीक्षण, निदेशन और प्रबंधन, मुख्य सूचना आयुक्त में निहित होगा, जिसकी सहायता सूचना आयुक्तों द्वारा की जाएगी और वह ऐसी सभी शक्तियों का प्रयोग और ऐसे सभी कार्य और बातें कर सकेगा, जिनका केन्द्रीय सूचना आयोग द्वारा स्वतंत्र रूप से इस अधिनियम के अधीन किसी अन्य प्राधिकारी के निदेशों के अधीन रहे बिना प्रयोग किया जा सकता है या जो की जा सकती है।

**Simplification:** मुख्य सूचना आयुक्त केंद्रीय सूचना आयोग को चलाते हैं और दूसरे आयुक्त उनकी मदद करते हैं। आयोग अपने फ़ैसले खुद लेता है, कोई और उसे आदेश नहीं देता।

**Analysis:** [TBD — written by the team]

## Case 12 — annotators: tie:condition/none

`rti-s15_7|en|perturbed` · gold 9.00 (± 1.00, Preserved) · predicted 9.02 (Preserved) · error type: scope · annotators' main change: tie:condition/none

**Original:** The headquarters of the State Information Commission shall be at such place in the State as the State Government may, by notification in the Official Gazette, specify and the State Information Commission may, with the previous approval of the State Government, establish offices at other places in the State.

**Simplification:** The State Government will choose the place in the State where the State Information Commission has its main office, and will announce it in the Official Gazette. The Commission may also open offices in other places in the State, but if the State Government agrees first.

**Analysis:** [TBD — written by the team]

## Case 13 — annotators: tie:condition/omission

`cpa-s51_4|en|aggressive` · gold 6.50 (± 2.50, Partially Preserved) · predicted 9.45 (Preserved) · error type: — · annotators' main change: tie:condition/omission

**Original:** Where the National Commission is satisfied that a substantial question of law is involved in any case, it shall formulate that question and hear the appeal on that question: Provided that nothing in this sub-section shall be deemed to take away or abridge the power of the National Commission to hear, for reasons to be recorded in writing, the appeal on any other substantial question of law, if it is satisfied that the case involves such question of law.

**Simplification:** The National Commission writes down the main legal question in a case and hears the appeal on it. It can also look at other important legal questions if it explains why.

**Analysis:** [TBD — written by the team]

## Case 14 — annotators: tie:date/time limit/number/amount

`rti-s19_3|en|perturbed` · gold 5.00 (± 0.00, Partially Preserved) · predicted 6.56 (Partially Preserved) · error type: number · annotators' main change: tie:date/time limit/number/amount

**Original:** A second appeal against the decision under sub-section (1) shall lie within ninety days from the date on which the decision should have been made or was actually received, with the Central Information Commission or the State Information Commission: Provided that the Central Information Commission or the State Information Commission, as the case may be, may admit the appeal after the expiry of the period of ninety days if it is satisfied that the appellant was prevented by sufficient cause from filing the appeal in time.

**Simplification:** A second appeal against a decision under sub-section (1) can be filed with the Central Information Commission or the State Information Commission within ninety days from the date the decision should have been made or was actually received. However, the Commission may accept the appeal after 120 days if it is satisfied that the appellant had a good reason for not filing it on time.

**Analysis:** [TBD — written by the team]

## Case 15 — annotators: tie:date/time limit/omission

`rti-s19_3|hi|aggressive` · gold 9.00 (± 0.00, Preserved) · predicted 5.46 (Partially Preserved) · error type: — · annotators' main change: tie:date/time limit/omission

**Original:** उपधारा (1) के अधीन विनिश्चय के विरुद्ध दूसरी अपील उस तारीख से, जिसको विनिश्चय किया जाना चाहिए था या वास्तव में प्राप्त किया गया था, नब्बे दिन के भीतर केन्द्रीय सूचना आयोग या राज्य सूचना आयोग को होगी : परन्तु, यथास्थिति, केन्द्रीय सूचना आयोग या राज्य सूचना आयोग नब्बे दिन की अवधि की समाप्ति के पश्चात् अपील को ग्रहण कर सकेगा, यदि उसका यह समाधान हो जाता है कि अपीलार्थी समय पर अपील फाइल करने से पर्याप्त कारण से निवारित किया गया था।

**Simplification:** पहली अपील से संतुष्ट न हों तो 90 दिन के अंदर सूचना आयोग में दूसरी अपील कर सकते हैं। देर होने पर भी सही कारण हो तो आयोग अपील सुन सकता है।

**Analysis:** [TBD — written by the team]

## Case 16 — annotators: tie:exception/omission

`rti-s9|en|perturbed` · gold 7.00 (± 2.00, Preserved) · predicted 8.61 (Preserved) · error type: exception_drop · annotators' main change: tie:exception/omission

**Original:** Without prejudice to the provisions of section 8, a Central Public Information Officer or a State Public Information Officer, as the case may be, may reject a request for information where such a request for providing access would involve an infringement of copyright subsisting in a person other than the State.

**Simplification:** Without affecting section 8, a Central or State Public Information Officer may refuse a request for information if giving access would break the copyright of a person.

**Analysis:** [TBD — written by the team]

## Case 17 — annotators: tie:none/obligation/permission

`rti-s14_1|hi|normal` · gold 9.50 (± 0.50, Preserved) · predicted 9.91 (Preserved) · error type: — · annotators' main change: tie:none/obligation/permission

**Original:** उपधारा (3) के उपबंधों के अधीन रहते हुए, मुख्य सूचना आयुक्त या किसी सूचना आयुक्त को राष्ट्रपति के आदेश द्वारा साबित कदाचार या असमर्थता के आधार पर उसके पद से तभी हटाया जाएगा, जब उच्चतम न्यायालय ने, राष्ट्रपति द्वारा उसे किए गए किसी निर्देश पर जांच के पश्चात् यह रिपोर्ट दी हो कि, यथास्थिति, मुख्य सूचना आयुक्त या सूचना आयुक्त को उस आधार पर हटा दिया जाना चाहिए।

**Simplification:** उपधारा (3) के प्रावधानों के अधीन, मुख्य सूचना आयुक्त या किसी सूचना आयुक्त को साबित कदाचार या असमर्थता के आधार पर केवल राष्ट्रपति के आदेश से पद से हटाया जा सकेगा। ऐसा तभी होगा जब राष्ट्रपति मामला उच्चतम न्यायालय को भेजें और उच्चतम न्यायालय जाँच के बाद यह रिपोर्ट दे कि उसे उस आधार पर हटाया जाना चाहिए।

**Analysis:** [TBD — written by the team]

## Case 18 — annotators: tie:none/omission

`cpa-s36_2|en|aggressive` · gold 9.50 (± 0.50, Preserved) · predicted 8.21 (Preserved) · error type: — · annotators' main change: tie:none/omission

**Original:** On receipt of a complaint made under section 35, the District Commission may, by order, admit the complaint for being proceeded with or reject the same: Provided that a complaint shall not be rejected under this section unless an opportunity of being heard has been given to the complainant: Provided further that the admissibility of the complaint shall ordinarily be decided within twenty-one days from the date on which the complaint was filed.

**Simplification:** When you file a consumer complaint, the District Commission decides whether to take it up, usually within 21 days. It has to listen to you before saying no.

**Analysis:** [TBD — written by the team]

## Case 19 — annotators: tie:none/other

`rti-s4_2|hi|perturbed` · gold 9.50 (± 0.50, Preserved) · predicted 9.11 (Preserved) · error type: modality · annotators' main change: tie:none/other

**Original:** प्रत्येक लोक अधिकारी का निरंतर यह प्रयास होगा कि वह उपधारा (1) के खंड (ख) की अपेक्षाओं के अनुसार, स्वप्रेरणा से, जनता को नियमित अन्तरालों पर संसूचना के विभिन्न साधनों के माध्यम से, जिनके अन्तर्गत इंटरनेट भी है, इतनी अधिक सूचना उपलब्ध कराने के लिए उपाय करे जिससे कि जनता को सूचना प्राप्त करने के लिए इस अधिनियम का कम से कम अवलंब लेना पड़े।

**Simplification:** हर लोक प्राधिकारी लगातार यह कोशिश करेगा कि उपधारा (1) के खंड (ख) के अनुसार वह खुद ही, नियमित अंतराल पर, इंटरनेट सहित संचार के अलग-अलग साधनों से जनता को ज़्यादा से ज़्यादा सूचना दे। इससे लोगों को सूचना पाने के लिए इस अधिनियम का कम से कम सहारा लेना पड़ सकेगा।

**Analysis:** [TBD — written by the team]

## Case 20 — annotators: tie:none/scope

`cpa-s83|en|aggressive` · gold 7.00 (± 3.00, Preserved) · predicted 7.29 (Preserved) · error type: — · annotators' main change: tie:none/scope

**Original:** A product liability action may be brought by a complainant against a product manufacturer or a product service provider or a product seller, as the case may be, for any harm caused to him on account of a defective product.

**Simplification:** If a broken or faulty product hurts you, you can take action against the company that made it, sold it or serviced it.

**Analysis:** [TBD — written by the team]
