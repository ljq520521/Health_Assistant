"""Rule-based, profile-driven exercise recommendations (member C).

The rules are deliberately transparent: the page shows the evidence behind each
suggestion so the user can judge it. This is general wellness guidance, not a
medical prescription, and it never reads data from other modules besides the
read-only profile and health goals that already exist.
"""

from datetime import date, timedelta

BMI_LABELS = (
    (18.5, "偏瘦"),
    (24.0, "正常范围"),
    (28.0, "超重"),
)
OVERWEIGHT_BMI = 28.0
LOW_BMI = 18.5
WEEK_DAYS = 7

FOCUS_LABELS = {
    "fat_loss": "减脂优先",
    "muscle_gain": "增肌优先",
    "shaping": "塑形优先",
    "maintain": "保持规律运动",
}
FOCUS_TARGETS = {"fat_loss": 200, "muscle_gain": 150, "shaping": 180, "maintain": 150}

# Checked in this order, so an explicit goal wins over a BMI-derived focus.
GOAL_KEYWORDS = {
    "fat_loss": ("减脂", "减重", "减肥", "瘦", "体重", "掉秤", "控脂"),
    "muscle_gain": ("增肌", "肌肉", "力量", "围度"),
    "shaping": ("塑形", "体态", "线条", "紧致"),
}

# Canonical activity names mapped to the words a profile might contain.
PREFERENCE_KEYWORDS = {
    "快走": ("快走", "健走", "走路", "散步"),
    "跑步": ("跑步", "慢跑"),
    "骑行": ("骑行", "单车", "自行车"),
    "游泳": ("游泳",),
    "瑜伽": ("瑜伽", "普拉提"),
    "力量训练": ("力量", "器械", "哑铃", "撸铁", "健身"),
    "跳绳": ("跳绳",),
    "球类": ("羽毛球", "篮球", "足球", "乒乓", "网球", "球类"),
    "舞蹈": ("舞蹈", "跳舞", "跳操", "有氧操"),
}


def bmi_of(profile: dict) -> float | None:
    height = profile.get("height_cm")
    weight = profile.get("weight_kg")
    if not height or not weight or height <= 0 or weight <= 0:
        return None
    return round(weight / ((height / 100) ** 2), 1)


def bmi_label(bmi: float | None) -> str | None:
    if bmi is None:
        return None
    for limit, label in BMI_LABELS:
        if bmi < limit:
            return label
    return "肥胖"


def preferred_types(goal_titles: list[str], preferences: str) -> list[str]:
    text = f"{preferences} {' '.join(goal_titles)}"
    return [name for name, words in PREFERENCE_KEYWORDS.items() if any(word in text for word in words)]


def focus_of(goal_titles: list[str], bmi: float | None) -> str:
    text = " ".join(goal_titles)
    for focus, words in GOAL_KEYWORDS.items():
        if any(word in text for word in words):
            return focus
    if bmi is not None and bmi >= 24:
        return "fat_loss"
    return "maintain"


def weekly_target(focus: str, bmi: float | None, has_medical_history: bool) -> int:
    target = FOCUS_TARGETS[focus]
    if focus == "fat_loss" and bmi is not None and bmi >= OVERWEIGHT_BMI:
        target = 225
    if bmi is not None and bmi < LOW_BMI:
        target = min(target, 120)
    if has_medical_history:
        target = min(target, 150)
    return target


def _week_records(records: list[dict], today: date) -> list[dict]:
    since = (today - timedelta(days=WEEK_DAYS - 1)).isoformat()
    end = today.isoformat()
    return [
        record
        for record in records
        if isinstance(record.get("record_date"), str) and since <= record["record_date"] <= end
    ]


def _minutes(record: dict) -> int:
    try:
        return max(0, int(record.get("duration_minutes") or 0))
    except (TypeError, ValueError):
        return 0


def build_recommendation(
    profile: dict,
    goal_titles: list[str],
    records: list[dict],
    today: date,
) -> dict:
    bmi = bmi_of(profile)
    label = bmi_label(bmi)
    focus = focus_of(goal_titles, bmi)
    medical = str(profile.get("medical_history") or "").strip()
    preferences = str(profile.get("preferences") or "").strip()
    target = weekly_target(focus, bmi, bool(medical))

    week = _week_records(records, today)
    done = sum(_minutes(record) for record in week)
    active_days = len({record["record_date"] for record in week})
    high_minutes = sum(_minutes(record) for record in week if record.get("intensity") == "high")
    high_ratio = high_minutes / done if done else 0
    today_minutes = sum(_minutes(record) for record in week if record["record_date"] == today.isoformat())
    progress = min(100, round(done / target * 100)) if target else 0
    preferred = preferred_types(goal_titles, preferences)

    if done >= target:
        summary = (
            f"最近 7 天已完成 {done} 分钟，达到本周 {target} 分钟的目标；"
            "接下来以稳定节奏和恢复为主，不必刻意加量。"
        )
    elif done == 0:
        summary = (
            f"最近 7 天还没有运动记录。先从每周 {target} 分钟、每次 20–30 分钟开始，"
            "比一次练很久更容易坚持。"
        )
    else:
        summary = (
            f"最近 7 天完成 {done} 分钟、覆盖 {active_days} 天，"
            f"距离本周 {target} 分钟的目标还差 {target - done} 分钟。"
        )

    suggestions = _suggestions(focus, target, done, today_minutes, high_ratio, bmi, preferred)
    safety_notes = _safety_notes(medical, bmi, high_ratio)
    evidence = _evidence(profile, goal_titles, bmi, label, preferences, target, done, active_days)

    return {
        "bmi": bmi,
        "bmi_label": label,
        "focus": focus,
        "focus_label": FOCUS_LABELS[focus],
        "weekly_target_minutes": target,
        "weekly_done_minutes": done,
        "weekly_progress_percent": progress,
        "days_active_last_week": active_days,
        "preferred_types": preferred,
        "summary": summary,
        "suggestions": suggestions,
        "safety_notes": safety_notes,
        "evidence": evidence,
    }


def _suggestions(
    focus: str,
    target: int,
    done: int,
    today_minutes: int,
    high_ratio: float,
    bmi: float | None,
    preferred: list[str],
) -> list[dict]:
    activity = preferred[0] if preferred else "快走"
    remaining = max(0, target - done)
    items = []

    if remaining:
        sessions = max(1, -(-remaining // 30))
        items.append(
            {
                "tag": "有氧",
                "title": f"本周还差 {remaining} 分钟",
                "detail": (
                    f"可以安排 {sessions} 次 30 分钟左右的{activity}，"
                    "分散到不同日期比一次练完更稳妥。"
                ),
            }
        )
    else:
        items.append(
            {
                "tag": "有氧",
                "title": "本周目标已完成",
                "detail": (
                    f"保持现在的节奏即可；如果恢复良好，可加 1 次 20–30 分钟低强度{activity}，"
                    "不必刻意加量。"
                ),
            }
        )

    if focus in ("muscle_gain", "shaping") or (bmi is not None and bmi >= 24):
        items.append(
            {
                "tag": "力量",
                "title": "每周 2 次力量训练",
                "detail": (
                    "每次 20–30 分钟，覆盖下肢、推、拉三类动作，如深蹲、俯卧撑、"
                    "弹力带划船；同一肌群间隔至少 48 小时。"
                ),
            }
        )
    else:
        items.append(
            {
                "tag": "力量",
                "title": "每周 1–2 次基础力量",
                "detail": "用自重或弹力带做深蹲、臀桥、俯卧撑，每次 15–20 分钟，帮助维持肌肉量。",
            }
        )

    if high_ratio >= 0.5:
        items.append(
            {
                "tag": "恢复",
                "title": "高强度占比偏高",
                "detail": (
                    f"最近 7 天高强度运动占 {round(high_ratio * 100)}%，"
                    "建议每周留 1–2 天做散步、拉伸或瑜伽等主动恢复。"
                ),
            }
        )
    else:
        items.append(
            {
                "tag": "恢复",
                "title": "训练后留出恢复时间",
                "detail": "每次运动后做 5–10 分钟拉伸；连续两天疲劳或睡眠不足时，改为低强度活动。",
            }
        )

    if today_minutes:
        items.append(
            {
                "tag": "今天",
                "title": f"今天已完成 {today_minutes} 分钟",
                "detail": "补充水分，留意身体感受；如果这是今天的第二次运动，注意总时长不要突然翻倍。",
            }
        )
    else:
        items.append(
            {
                "tag": "今天",
                "title": "今天还没有运动记录",
                "detail": f"安排 20–30 分钟{activity}就能推进本周目标；久坐时每小时起来活动 3–5 分钟。",
            }
        )

    return items


def _safety_notes(medical: str, bmi: float | None, high_ratio: float) -> list[str]:
    notes = []
    if medical:
        notes.append(
            "档案中有既往病史记录：开始新的训练计划前请先咨询医生；"
            "出现胸痛、眩晕或异常气短时立即停止运动。"
        )
    if bmi is not None and bmi < LOW_BMI:
        notes.append("BMI 偏低：优先保证能量摄入与力量训练，避免长时间高强度有氧。")
    if bmi is not None and bmi >= OVERWEIGHT_BMI:
        notes.append("体重基数较大：优先选择快走、游泳、骑行等低冲击有氧，循序渐进增加时长。")
    if high_ratio >= 0.5:
        notes.append("高强度运动占比偏高，注意睡眠与恢复，避免连续多天高强度训练。")
    return notes


def _evidence(
    profile: dict,
    goal_titles: list[str],
    bmi: float | None,
    label: str | None,
    preferences: str,
    target: int,
    done: int,
    active_days: int,
) -> list[str]:
    lines = []
    height, weight = profile.get("height_cm"), profile.get("weight_kg")
    if bmi is not None:
        lines.append(f"身高 {height:g} cm、体重 {weight:g} kg，BMI {bmi}（{label}）")
    else:
        lines.append("档案里还没有完整的身高体重，BMI 相关建议暂不计算")
    if goal_titles:
        lines.append("健康目标：" + "、".join(goal_titles[:3]))
    if preferences:
        lines.append(f"运动偏好：{preferences}")
    if str(profile.get("medical_history") or "").strip():
        lines.append("档案记录了既往病史，本周目标按时长更保守的 150 分钟以内设定")
    lines.append(f"最近 7 天：{active_days} 天有记录，共 {done} 分钟；建议目标 {target} 分钟/周")
    return lines
