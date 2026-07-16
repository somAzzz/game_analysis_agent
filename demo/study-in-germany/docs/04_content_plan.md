# 内容计划

## 行动卡

MVP 当前使用 43 张行动卡，覆盖申请季、学业、德语、行政、金钱、社交、心理、生活和职业路线。每张卡包含消耗、收益、风险标签和条件。

## 事件

MVP 当前使用 126 个事件，已全部集成在 `autoload/DataRegistry.gd`：

- 固定事件：关键周数必定出现，用于保证 20 周 Demo 有明确节奏。
- 条件事件：由学业、德语、金钱、压力、孤独、饥饿、行政熟练度和隐藏 flag 触发。
- 随机事件：按权重抽取，用于制造德国留学生活的偶发感。
- 每个事件运行时都有 4 个选项，每个选项都有独立的成功变化、失败变化、基础成功率和属性成功率系数。

关键事件链包括 APS 申请季、APS 未达标补救、APS 成绩对应大学定位、TestDaF 4x4、德国高价语言班、语言证明卡注册、错过注册窗口、下学期注册、找房/WG 面试、学校注册卡课、Ausländerbehörde 没有 Termin、居留风险升级、学生合法打工时长说明、按 2026 最低工资结算的合法工时、超工时风险、没钱后的低价黑工诱惑、黑工后续风险、第一次教授邮件、第一次 Klausur、父母视频电话、圣诞节孤独、饥饿与同学饭局、同学喝酒、情感对象分歧、稳定关系做饭、高消费约会、被欺骗感情、打工学业冲突、德国同学组队、考试报名、学期费、冻结账户、职业方向和心理健康。

现实流程校正见 `docs/08_chinese_student_germany_process_research.md`。当前冻结账户按 2026 年常见学生签证金额 `11,904 EUR/年`、`992 EUR/月`建模，保险扣费按 2026 年学生保险约 `141-146 EUR/月`建模。

完整的 504 个选项数值变化见 `docs/05_event_choice_balance.md`。

### 核心事件清单

下方保留关键事件清单作为策划索引；完整事件与 4 选项数值以 `docs/05_event_choice_balance.md` 的自动导出为准。

1. `aps_start` - 申请季开始：APS
2. `testdaf_requirement_notice` - TestDaF 4x4 要求
3. `aps_not_ready` - APS 还没达标
4. `aps_elite_university_options` - APS 高分定位
5. `aps_mid_university_options` - APS 稳妥定位
6. `aps_low_university_options` - APS 低空通过
7. `arrival` - 抵达德国
8. `germany_language_track_start` - 德国继续读语言
9. `testdaf_blocks_enrollment` - TestDaF 卡住注册
10. `first_lecture` - 第一次上课
11. `missing_school_registration` - 注册没完成，上不了课
12. `registration_window_missed` - 错过学校注册窗口
13. `wg_interview` - WG 面试
14. `legal_work_limit_notice` - 学生打工时长说明
15. `anmeldung_deadline` - Anmeldung 提醒
14. `midterm_pressure` - 期中压力
15. `group_invite` - 德国同学邀你组队
16. `exam_week` - 第一次 Klausur
17. `semester_wrap` - 学期快结束了
18. `termin_missing` - Ausländerbehörde 没有 Termin
19. `visa_status_hidden_check` - 居留期限临近
20. `deportation_risk_notice` - 居留风险升级
21. `rent_pressure` - 房租压力
22. `burnout_warning` - 身体发出警告
23. `lonely_christmas` - 一个人的节日
24. `academic_gap` - 课程听不懂
25. `language_wall` - 德语墙
26. `job_study_conflict` - 打工和学习撞车
27. `work_limit_exceeded_warning` - 打工时长越线
28. `desperate_illegal_work_offer` - 没钱后的黑工诱惑
29. `annual_work_limit_warning` - 年度打工额度用尽
30. `illegal_cash_job_offer` - 现金黑工邀请
31. `illegal_work_followup` - 黑工后续风险
29. `parents_future` - 父母问未来
30. `prof_email` - 第一次给教授写邮件
31. `health_insurance_letter` - 保险来信
32. `project_presentation` - Presentation 临近
33. `cheap_ticket` - 廉价火车票
34. `flat_kitchen` - WG 厨房会议
35. `student_discount` - 学生优惠
36. `classmate_home_dinner` - 去同学家吃饭
37. `drinks_with_classmates` - 同学约你喝酒
38. `romance_crossroads` - 感情支线开端
39. `stable_partner_cooking` - 稳定关系的一顿饭
40. `expensive_partner_weekend` - 高消费对象的周末计划
41. `romance_scam_risk` - 被欺骗感情的风险
42. `romance_bankruptcy_warning` - 感情开销失控
43. `relationship_support_exam` - 稳定关系的考前支持
44. `library_friend` - 图书馆熟脸
45. `mailbox_shock` - 信箱惊吓
46. `spati_talk` - 深夜便利店闲聊
47. `rainy_week` - 连续阴雨
48. `course_forum` - 课程论坛救命帖
49. `grocery_inflation` - 超市价格刺眼
50. `bike_offer` - 二手自行车
51. `club_poster` - 社团海报
52. `coding_hackathon` - Hackathon 邀请
53. `prof_reply` - 教授回信
54. `anna_coffee` - Anna 约咖啡
55. `li_anxiety` - 李同学转发群消息
56. `parents_package` - 家里寄来的包裹
57. `tax_id_letter` - 税号到了
58. `laundry_fail` - 洗衣事故
59. `mensa_surprise` - 食堂惊喜
60. `wrong_platform` - 坐错站台
61. `neighbor_noise` - 邻居派对
62. `bank_card_delay` - 银行卡还没到
63. `career_fair` - 校园招聘会
64. `exam_old_paper` - 找到往年题
65. `sick_day` - 感冒
66. `roommate_help` - 室友帮忙
67. `moodle_down` - Moodle 崩了
68. `refund` - 意外退款
69. `winter_dark` - 天黑太早
70. `deadline_extension` - 延期机会
71. `quiet_success` - 一个小小的顺利
72. `registration_queue` - 注册办公室排队
73. `sim_card_confusion` - 电话卡套餐
74. `cash_only_place` - 只收现金
75. `pfand_machine` - 押金瓶机器
76. `sunday_closed` - 周日超市关门
77. `semester_ticket` - 学期票激活
78. `lost_in_campus` - 校园迷路
79. `moodle_quiz` - Moodle 小测
80. `lab_partner_absent` - 实验搭档失联
81. `office_hour_full` - 答疑预约满了
82. `tutorium_help` - Tutorium 救场
83. `exam_registration` - 考试报名
84. `missed_exam_registration` - 差点错过考试报名
85. `deutsch_phrase_win` - 一句德语说顺了
86. `accent_misunderstood` - 口音误会
87. `deep_l_trap` - 翻译器陷阱
88. `room_contract_clause` - 租房合同条款
89. `heating_argument` - 暖气温度争论
90. `trash_sorting_test` - 垃圾分类考试
91. `deposit_worry` - 押金焦虑
92. `family_compare` - 亲戚比较
93. `parents_money_hint` - 父母暗示开销
94. `homesick_food` - 想家的一顿饭
95. `wechat_silence` - 朋友圈沉默
96. `friend_back_home` - 国内朋友升职
97. `student_job_offer` - 临时工机会
98. `boss_extra_shift` - 老板加班请求
99. `payslip_question` - 工资单疑惑
100. `hiwi_hint` - HiWi 暗示
101. `linkedin_message` - LinkedIn 私信
102. `cv_language_choice` - 简历语言选择
103. `career_doubt` - 职业方向怀疑
104. `presentation_applause` - Presentation 掌声
105. `presentation_freeze` - Presentation 卡壳
106. `plagiarism_warning` - 引用格式警告
107. `library_workshop` - 图书馆文献课
108. `blocked_account_notice` - 冻结账户提醒
109. `insurance_payment` - 保险扣费
110. `semester_fee_due` - 学期费提醒
111. `refund_from_landlord` - 房东退小额费用
112. `city_registration_letter` - 市政厅来信
113. `train_strike` - 火车罢工
114. `bike_flat_tire` - 自行车爆胎
115. `doctor_appointment` - 预约医生
116. `pharmacy_advice` - 药房建议
117. `mental_health_webinar` - 心理健康讲座
118. `snow_day` - 第一场雪
119. `neighbor_greeting` - 邻居打招呼
120. `international_potluck` - 国际学生聚餐
121. `after_exam_void` - 考后空虚

## NPC

- 李同学：中国同学，提供信息和内卷压力。
- Anna：德国同学，影响组队、德语和融入。
- Cem：WG 室友，影响住房、生活和社交。
- Müller 教授：影响邮件、HiWi、论文路线。
- 父母：提供经济支持和家庭压力。

## 结局

16 个 Demo 结局全部在第一学期结算时判断。结局以状态组合和隐藏 flag 为准，不使用单一总分。注册失败、被迫离境、现金流断裂、生活失衡、高压休整、打工违规风险和感情破产属于严重失败/生存危机类，优先级高于普通成功路线；延迟入学会覆盖普通成功，勉强撑住作为兜底结局。
