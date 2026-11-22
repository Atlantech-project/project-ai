<div dir="rtl">

# تقرير التحقق بعد الدمج: AI-055 (تصحيح الاختبارات) و AI-058 و AI-059

**التاريخ:** 2026-11-22 · **رأس `develop` النهائي:** `e395bac` · **المرجع الداخلي:** `docs/tasks/AUTONOMOUS_EXECUTION_PLAN.md` §0j (Checkpoint 12)

## 1. الملخص التنفيذي

- **دُمجت ثلاثة فروع من أربعة:** AI-055 (تصحيح الاختبارات)، AI-058، AI-059.
- **الفرع الرابع لم يُدمج:** `feature/SETUP-replan-batch-records` (PR #70) ما زال **مفتوحًا**، وصار يتعارض مع `develop` في `WORK_STATUS.md`. أنشأتُ فرعًا بديلًا يحمل محتواه كما هو، والتوصية إغلاق #70 دون دمج.
  - ملاحظة: "SETUP second-batch records" المذكور في رسالتك هو PR #66، وقد دُمج في الجولة السابقة.
- **المزامنة:** `develop` المحلي مطابق لـ `origin/develop`، ومؤشر PortHub على `e395bac`، والملفات المشتركة متزامنة.
- **الاختبارات:** المجموعة الكاملة على `e395bac`: 2351 passed، 51 skipped، 1 xfailed، و CI أخضر.
- **فجوة سُدّت:** حفظ FIFO و NO_FEASIBLE_PLAN كان مُختبرًا بمستودع وهمي فقط، فأضفتُ اختبارَي MySQL على فرع مستقل.
- **الحالات:**
  - AI-058: BLOCKED (INT-B11 لإعادة التوليد فقط).
  - AI-059: IN PROGRESS، وليست DONE: معالج المهام لم يُبنَ بعد، وصار ممكنًا بعد دمج AI-058.

## 2. التحقق من GitHub

| PR | الفرع | الـ head | الدمج | الوقت (UTC) | الحالة |
|---|---|---|---|---|---|
| #67 | `feature/AI-055-random-instance-tugs` | `47051a7` | `a45192a` | 14:55:06 | مدموج |
| #68 | `feature/AI-058-recommendation-persistence` | `229787c` | `e1576a8` | 14:55:17 | مدموج |
| #69 | `feature/AI-059-started-components-replan` | `10427ed` | `e395bac` | 14:59:56 | مدموج |
| #70 | `feature/SETUP-replan-batch-records` | `c3123ff` | — | — | **مفتوح، غير مدموج** |

- **CI على `e395bac`:** `ci-ok`، `lint`، `tests`، `typecheck`، `secret-scan`، كلها ناجحة.
- **الـ PRs المفتوحة:** #70 فقط، ولا يوجد PR مكرر.
- **المحتوى:** كل ملف مدموج مطابق حرفيًا للـ commit المدفوع، ولا توجد علامات تعارض. لكن `develop` يحمل صفًّا قديمًا مكررًا لـ `SETUP-r12-merge-records` (إصلاحه كان في #70)، وقد أُزيل في الفرع البديل.

## 3. مزامنة المستودعات

- **`develop` المحلي:** تقدّم بـ fast-forward فقط إلى `e395bac`، مطابقًا لـ `origin/develop`. ملفاتك غير المتتبعة الثلاثة في `reports/` بقيت كما هي.
- **مؤشر PortHub:** نُقل `project-ai` من `254757c` إلى `e395bac` في commit مستقل على `main` (`e3e1273`)، وتأكّد ذلك على `origin/main`. تغيّر الـ gitlink وحده.
- **الملفات المشتركة مقابل PortHub `main`:**

| الملف | النتيجة |
|---|---|
| `schema.sql` | SHA-256 متطابق (`afdfaadc…`)، والمانيفست يشير إلى `d55a263` |
| `ATLANTECH_Decisions.md` | متطابق حرفيًا حتى عنوان `## AI task decisions` |
| مخططات JSON للحمولات و `table-ownership.md` | متطابقة |
| `ATLANTECH_Contracts.md` | النص التعاقدي متطابق. الفروق الوحيدة تكييفات محلية قديمة (قاعدة عدم السجلات، ملاحظة النسخ، وعبارة "PortHub `contracts/…`" بدل الروابط النسبية)، ولا يختلف أي إصدار أو حالة أو صف |

## 4. التحقق من AI-058

| المطلوب | النتيجة | الدليل |
|---|---|---|
| حفظ أول توصية في معاملة واحدة | ✔ | MySQL: `test_a_first_recommendation_is_written_and_fully_traceable` (من التشغيل إلى التوصية والخيارات والقاطرات والعوامل ونسخ النماذج، مكتملًا عبر `write_done`) |
| حفظ مقترح `DELAY_REPLAN` | ✔ | MySQL: `test_a_delay_replan_proposal_is_written_next_to_the_confirmed_version` (النسخة CONFIRMED لا تُمس) |
| حفظ FIFO و NO_FEASIBLE_PLAN | ✔ بعد سدّ الفجوة | كانت اختبارات وحدة فقط؛ أُضيف اختباران على MySQL في `feature/AI-058-fifo-infeasible-mysql-tests` (`bb1c5f5`)، والنتيجة 7 من 7 محليًا |
| إعادة التوليد مرفوضة صراحةً بسبب INT-B11 قبل أي كتابة | ✔ | MySQL، للحالتين `PENDING_REVIEW` و `MODIFIED_BY_STAFF`؛ الرسالة تذكر INT-B11 والفئة `PRECONDITION_FAILED` |
| بقاء النسخة السابقة قائمة عند فشل إعادة التوليد | ✔ | الاختبار نفسه، إضافةً إلى أن تشغيلًا بلا خطة ممكنة يترك النسخة `PENDING_REVIEW` كما هي (الاختبار الجديد) |
| الحفاظ على سلوك CT-10 v1.1 المعتمد | ✔ | وحدة: `PILOT_RANK_LIMIT` ← `PILOT_UNAVAILABLE`، و `TUG_COUNT` ← `TUG_UNAVAILABLE`، ورفض أي كود خارج القائمة. MySQL (الاختبار الجديد): `TUG_COUNT` يُخزَّن `TUG_UNAVAILABLE` |

**الحالة:** BLOCKED (INT-B11، لمسار إعادة التوليد فقط). المعياران الأول والثالث متحققان، والثاني مفتوح لإعادة التوليد.

## 5. التحقق من AI-059

| المطلوب | النتيجة | الدليل |
|---|---|---|
| أحداث `STARTED` و `DONE` تحدد المكونات المبدوءة | ✔ | MySQL: `test_begun_components_of_a_run_request_are_read_with_their_resource`. الصف `CONSUMED` يُحتسب و `RELEASED` لا يُحتسب أبدًا، ولا تُقرأ مكونات طلبات خارج التشغيل |
| بقاء الموارد والفترات الزمنية دون تغيير | ✔ | `test_a_started_berth_pilot_and_tug_stay_unchanged`، و `test_the_started_interval_wins_over_the_b3_estimate` |
| البدائل و FIFO لا تستطيع نقل المكونات المبدوءة | ✔ | `test_alternatives_keep_the_pin_when_the_berth_is_free`، و `test_fifo_keeps_the_pin_too`، و 8 حالات عشوائية، وفحص لاحق داخل الحل يرفض أي خيار يخالف التثبيت |
| المورد المبدوء غير المتاح يؤدي إلى NO_FEASIBLE_PLAN | ✔ | `test_a_started_tug_that_is_now_out_of_service_is_never_swapped` (قاطرة في `MAINTENANCE`)، وخارج النافذة ← `ENTRY_WINDOW` |
| توثيق معايير المعالج المتبقية بدقة | ✔ | المعيار 1 ("Each trigger tested") جزئي: النطاق مُختبر والمعالج غير مبني. المعيار 2 مفتوح هنا ومضمون في AI-058. إعادة التوليد معطّلة بـ INT-B11 |

**الحالة:** IN PROGRESS، وليست DONE. زال عائق "دمج AI-058"، وبناء المعالج هو الخطوة التالية في التاسك نفسها.

## 6. التحقق من اختبارات الحالات العشوائية

- **اختبار تغيير متعمّد (mutation):** أعدتُ الدالة القديمة الخاطئة في الذاكرة فقط، ففشلت الاختبارات الخمسة المصححة كلها على حواجزها الجديدة:
  - خصائص AI-055، وحد الوقت في AI-055؛
  - مرشح FIFO و اختبار الـ 12 ثانية في AI-056؛
  - العوامل العشوائية في AI-057.
- **بالدالة الصحيحة:** بذور الخصائص تضع 5، 4، 4، 2، 4، 3، 2، 1، 3، 3، 2، 3 طلبات (36 من 72)، وبذور FIFO تضع 5، 5، 5، 2، 1، 3.
- **النتيجة:** لم يعد ممكنًا أن تنجح هذه الاختبارات لمجرد أن كل الطلبات استُبعدت.

## 7. الاختبارات

| الأمر | البيئة | النتيجة |
|---|---|---|
| `pytest -q` كامل | `develop` `e395bac`، MySQL 8.4 و Redis 7.4 محليًا (بيئة CI) | PASSED: 2351 passed، 51 skipped، 1 xfailed |
| `ruff check` و `ruff format --check` و `mypy` (171 ملفًا) | `e395bac` | نظيفة |
| اختبارات AI-058 و AI-059 بالأسماء (68 اختبارًا) | `e395bac`، MySQL | PASSED كلها |
| `pytest -q tests/integration/test_persist.py` | فرع الاختبارات الجديد، MySQL | PASSED: 7 passed |
| `pytest -q -m "not integration"` | فرع الاختبارات الجديد | PASSED: 1868 passed، 50 skipped |
| اختبار التغيير المتعمّد | `e395bac` | فشلت الحواجز الخمسة كما يجب |
| CI على GitHub | `e395bac` | كل الفحوص الخمسة ناجحة |

العدد 2351 = 2281 + 39 (AI-058) + 31 (AI-059). لم يُتخطَّ أي اختبار ولم يُضعَف.

## 8. السجلات

- **`WORK_STATUS.md`:** أُزيل الصف المكرر، وسُجّلت PRs من #64 إلى #69، و AI-059 صار IN PROGRESS، وتاسك #70 صار SUPERSEDED.
- **Checkpoint 10:** جدوله تاريخي، والحالات الحالية في Checkpoint 12:

| التاسك | الحالة |
|---|---|
| AI-057 | BLOCKED (INT-Q4، R11 (a)) |
| AI-058 | BLOCKED (INT-B11) |
| AI-059 | IN PROGRESS |
| AI-070 | BLOCKED (INT-B6) |
| AI-071 | BLOCKED (R9، TR-11، OD-17) |
| AI-092 | DONE |

- **ما بقي كما هو:** التوصيات R9 و R11 (a) و R13 و R14، والطلبات الخارجية INT-B1 و INT-B6 و INT-B11 و INT-Q4، وأكواد الحالة الميدانية من الـ Backend.

## 9. العوائق

| العائق | المالك | يعطّل |
|---|---|---|
| INT-B11 (كتابة إعادة التوليد مقابل `uq_rec_active`) | Backend و Leads Council (R13) | إعادة التوليد في AI-058، و MANUAL و RESOURCE_CHANGE في AI-059 |
| INT-B1 (اعتماد كودي CT-10 المقترحين) | Backend | ليس بوابة؛ دقة الكود المعروض فقط |
| INT-Q4 و R11 (a) | QA / المراجع؛ AI Team | AI-057 |
| R9، TR-11، OD-17، INT-B6 | AI Team؛ Backend | AI-071 و AI-070 |

## 10. الفروع المفتوحة وترتيب الدمج

1. `feature/AI-058-fifo-infeasible-mysql-tests` (`bb1c5f5`): اختبارات وسجل AI-058 فقط.
2. `feature/SETUP-post-merge-replan-records`: السجلات و Checkpoint 11 و 12 وهذا التقرير.

**أغلق PR #70 دون دمج**، فمحتواه منقول بالكامل إلى الفرع 2. انقل مؤشر PortHub بعد كل دمج.

## 11. الخطوات التالية بالضبط

1. ادمج الفرعين بالترتيب أعلاه، وأغلق #70.
2. انقل مؤشر PortHub إلى رأس `develop` الجديد.
3. **في التاسك نفسه (AI-059، وليست دفعة جديدة):** ابنِ معالج PART2_SOLVE على فرع جديد من `develop`:
   - النطاق ← لقطة AI-050 ← B2 حتى B6 مع التثبيت ← AI-058؛
   - اختبار سيناريو لكل trigger؛
   - فحص "pending only" لـ RESOURCE_CHANGE؛
   - إبقاء إعادة التوليد مرفوضة حتى INT-B11.
4. ارفع R13 / INT-B11 إلى فريق الـ Backend و Leads Council، وأكّد R14.

</div>
