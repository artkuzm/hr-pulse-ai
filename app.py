import json
import os
from google import genai
from google.genai import types
import streamlit as st

# Настройка страницы
st.set_page_config(
    page_title="HR Pulse AI — Адаптация новичков",
    page_icon="🏃",
    layout="wide",
)

# Получение ключа из Secrets (для облака) или переменных окружения
api_key = None
try:
    api_key = st.secrets.get("GEMINI_API_KEY")
except Exception:
    pass

if not api_key:
    api_key = os.environ.get("GEMINI_API_KEY")

# Начальные синтетические данные (имитация базы сотрудников на испытательном сроке)
INITIAL_DATA = [
    {
        "id": 1,
        "name": "Елена Ковалева",
        "department": "Розница (ТЦ Мега)",
        "role": "Продавец-консультант",
        "days": 38,
        "answers": {
            "q1": (
                "План горит, а я половину беговых кроссовок по характеристикам не"
                " знаю."
            ),
            "q2": (
                "Наставник вечно в телефоне или на перекуре, спрашивать"
                " неудобно."
            ),
            "q3": (
                "Чувствую себя брошенной, думаю, может продажи спорттоваров —"
                " это вообще не мое."
            ),
        },
        "ai_result": {
            "risk_level": "HIGH",
            "risk_score": 88,
            "key_pain": "Отсутствие наставника и пробелы в товаре",
            "analysis": (
                "Критическая точка на 2-м месяце: сотрудник не знает"
                " ассортимент, боится задавать вопросы и уже задумывается об"
                " увольнении. Высокий риск ухода в ближайшие 1-2 недели."
            ),
            "hr_action": (
                "Провести личную встречу с Еленой, сменить наставника или"
                " назначить старшего продавца для разбора линейки беговой"
                " обуви."
            ),
            "bitrix_task_title": (
                "СРОЧНО: Риск увольнения — Елена Ковалева (Розница, 38 день)"
            ),
        },
        "bitrix_sent": False,
    },
    {
        "id": 2,
        "name": "Дмитрий Волков",
        "department": "Оптовый отдел",
        "role": "Менеджер по продажам",
        "days": 21,
        "answers": {
            "q1": "Холодные звонки идут тяжело, база старая, много отказов.",
            "q2": (
                "Коллектив отличный, руководитель отдела помогает со скриптами."
            ),
            "q3": (
                "Долго согласовываются счета в 1С, из-за этого клиенты"
                " остывают."
            ),
        },
        "ai_result": {
            "risk_level": "MEDIUM",
            "risk_score": 45,
            "key_pain": "Сложности с холодной базой и 1С",
            "analysis": (
                "Сотрудник мотивирован и чувствует поддержку команды, но"
                " сталкивается с техническими барьерами (старая база и долгая"
                " 1С). Есть риск постепенного выгорания."
            ),
            "hr_action": (
                "Передать обратную связь руководителю опта по обновлению базы и"
                " провести 30-минутный тренинг по ускорению работы в 1С."
            ),
            "bitrix_task_title": (
                "Внимание: Помощь с 1С и базой — Дмитрий Волков (Опт, 21 день)"
            ),
        },
        "bitrix_sent": False,
    },
    {
        "id": 3,
        "name": "Алексей Смирнов",
        "department": "Склад",
        "role": "Кладовщик-комплектовщик",
        "days": 14,
        "answers": {
            "q1": (
                "Нормально, втянулся в ритм, собираю заказы почти без ошибок."
            ),
            "q2": (
                "Старший смены адекватный, показал как перезагружать терминал"
                " сбора данных."
            ),
            "q3": "Спина немного устает с непривычки, но это мелочи.",
        },
        "ai_result": {
            "risk_level": "LOW",
            "risk_score": 12,
            "key_pain": "Адаптация проходит в штатном режиме",
            "analysis": (
                "Физическая усталость на 2-й неделе для склада — норма. Есть"
                " контакт с руководителем и понятные рабочие процессы, риск"
                " ухода минимальный."
            ),
            "hr_action": (
                "Плановый контроль на 30-й день, дополнительных действий не"
                " требуется."
            ),
            "bitrix_task_title": "Плановый чек-ап: Алексей Смирнов (Склад)",
        },
        "bitrix_sent": False,
    },
]

# Инициализация состояния сессии
if "employees" not in st.session_state:
    st.session_state.employees = INITIAL_DATA.copy()


def analyze_with_ai(current_api_key, name, department, role, days, q1, q2, q3):
    """Отправляет ответы новичка в Gemini и возвращает структурированный JSON."""
    if not current_api_key:
        st.error(
            "⚠️ Не найден API-ключ! Введите его в боковой панели слева."
        )
        return None

    client = genai.Client(api_key=current_api_key)

    system_prompt = """
    Ты — опытный HR-аналитик в крупной компании по продаже спорттоваров (400 человек: розничные магазины, склад, отдел оптовых продаж, офис).
    Твоя задача — оценить риск увольнения нового сотрудника на испытательном сроке (до 90 дней) по его ответам на еженедельный Pulse-опрос.
    
    Учитывай специфику отдела и стаж: на 7-й день незнание программ — норма, но на 30-60 день отсутствие помощи наставника или конфликты — критический риск ухода.
    
    Верни ответ СТРОГО в формате JSON со следующими ключами:
    {
      "risk_level": "HIGH" или "MEDIUM" или "LOW",
      "risk_score": целое число от 0 до 100,
      "key_pain": "Главная проблема в 3-5 словах",
      "analysis": "Краткий аналитический вывод о состоянии сотрудника и скрытых рисках (2 предложения)",
      "hr_action": "Конкретная рекомендация для HR или руководителя (1-2 предложения)",
      "bitrix_task_title": "Готовый заголовок задачи в Битрикс24 для наставника или руководителя"
    }
    """

    user_prompt = f"""
    Сотрудник: {name}
    Отдел: {department}
    Должность: {role}
    День работы в компании: {days}-й день
    
    Ответы на Pulse-опрос:
    1. Как прошла неделя и какие были трудности: {q1}
    2. Хватает ли помощи наставника и команды: {q2}
    3. Что больше всего раздражает или мешает: {q3}
    """

    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        st.error(f"Подробности ошибки: {e}")
        return None

# Боковая панель
with st.sidebar:
    st.header("⚙️ Настройки прототипа")
    if not api_key:
        api_key = st.text_input("Введите Gemini API Key", type="password")
        st.caption("Бесплатный ключ можно получить на Google AI Studio")
    else:
        st.success("✅ API-ключ подключен")

    st.divider()
    st.markdown("""
    **О проекте:**
    Система раннего выявления риска увольнения новичков (до 90 дней).
    
    * **Стек:** Python, Streamlit, Llama 3.3 70B.
    * **Интеграция:** Эмуляция постановки задач в Битрикс24.
    """)

# Заголовок приложения
st.title("🏃 Пульс Новичка AI")
st.caption(
    "Система раннего выявления риска увольнения на испытательном сроке (0–90"
    " дней)"
)

# Две основные вкладки
tab_hr, tab_newbie = st.tabs(
    ["📊 Дашборд HR и руководителей", "📝 Пройти опрос (глазами новичка)"]
)

# ==========================================
# ВКЛАДКА 1: ДАШБОРД HR И РУКОВОДИТЕЛЕЙ
# ==========================================
with tab_hr:
    employees = st.session_state.employees

    # Верхние метрики
    total = len(employees)
    high_risk = sum(
        1 for e in employees if e["ai_result"]["risk_level"] == "HIGH"
    )
    med_risk = sum(
        1 for e in employees if e["ai_result"]["risk_level"] == "MEDIUM"
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Новичков на контроле", f"{total} чел.")
    col2.metric(
        "🔴 Высокий риск ухода", f"{high_risk} чел.", delta_color="inverse"
    )
    col3.metric("🟡 Требуют внимания", f"{med_risk} чел.")

    st.divider()

    # Фильтр по уровню риска
    filter_risk = st.radio(
        "Показать сотрудников:",
        [
            "Все",
            "🔴 Только высокий риск",
            "🟡 Средний риск",
            "🟢 Всё хорошо",
        ],
        horizontal=True,
    )

    # Сортируем: самые проблемные сверху (по убыванию балла риска)
    sorted_employees = sorted(
        employees, key=lambda x: x["ai_result"]["risk_score"], reverse=True
    )

    for emp in sorted_employees:
        risk = emp["ai_result"]["risk_level"]

        # Применяем фильтр
        if filter_risk == "🔴 Только высокий риск" and risk != "HIGH":
            continue
        if filter_risk == "🟡 Средний риск" and risk != "MEDIUM":
            continue
        if filter_risk == "🟢 Всё хорошо" and risk != "LOW":
            continue

        # Карточка сотрудника
        with st.container(border=True):
            # Левая колонка в 3 раза шире правой
            c_left, c_right = st.columns([3, 1])

            with c_left:
                if risk == "HIGH":
                    st.subheader(
                        f"🔴 {emp['name']} — {emp['role']} ({emp['days']}-й"
                        " день)"
                    )
                elif risk == "MEDIUM":
                    st.subheader(
                        f"🟡 {emp['name']} — {emp['role']} ({emp['days']}-й"
                        " день)"
                    )
                else:
                    st.subheader(
                        f"🟢 {emp['name']} — {emp['role']} ({emp['days']}-й"
                        " день)"
                    )

                st.caption(
                    f"Подразделение: **{emp['department']}** | Индекс риска:"
                    f" **{emp['ai_result']['risk_score']}/100**"
                )
                st.markdown(
                    f"**Ключевая проблема:** {emp['ai_result']['key_pain']}"
                )
                st.write(f"**Анализ ИИ:** {emp['ai_result']['analysis']}")
                st.info(
                    f"💡 **Рекомендация HR:** {emp['ai_result']['hr_action']}"
                )

                with st.expander("Посмотреть исходные ответы сотрудника"):
                    st.write(f"**1. Неделя и трудности:** {emp['answers']['q1']}")
                    st.write(
                        f"**2. Помощь наставника:** {emp['answers']['q2']}"
                    )
                    st.write(f"**3. Что мешает:** {emp['answers']['q3']}")

            with c_right:
                st.write("**Действие в Битрикс24:**")
                if emp["bitrix_sent"]:
                    st.success("✅ Задача создана в Б24")
                    st.caption(f"Тема: {emp['ai_result']['bitrix_task_title']}")
                else:
                    if st.button(
                        "📤 Поставить задачу в Б24",
                        key=f"btn_{emp['id']}",
                        use_container_width=True,
                    ):
                        emp["bitrix_sent"] = True
                        st.rerun()
# ==========================================
# ВКЛАДКА 2: ОПРОС НОВИЧКА
# ==========================================
with tab_newbie:
    st.subheader("Еженедельный Pulse-опрос сотрудника")
    st.write(
        "В реальной работе ссылка на этот опрос приходит новичку в"
        " Telegram/Битрикс24 на 7, 14, 30 и 60 день работы."
    )

    with st.form("pulse_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            name = st.text_input("Имя и Фамилия", value="Игорь Соколов")
            department = st.selectbox(
                "Подразделение",
                [
                    "Розница (Магазин)",
                    "Склад",
                    "Оптовый отдел",
                    "Офис / Бэк-офис",
                ],
            )
        with col_b:
            role = st.text_input("Должность", value="Продавец-кассир")
            days = st.slider("Какой день вы работаете в компании?", 1, 90, 25)

        st.divider()
        q1 = st.text_area(
            "1. Как прошла эта неделя? Что получилось, а с чем возникли"
            " трудности?",
            value=(
                "Покупателей много, на кассе постоянно очереди, программа"
                " зависает при оформлении возврата."
            ),
        )
        q2 = st.text_area(
            "2. Хватает ли вам помощи от наставника и коллег?",
            value=(
                "Все бегают в запаре, лишний раз боюсь дергать, чтобы не"
                " наорали."
            ),
        )
        q3 = st.text_area(
            "3. Что сейчас больше всего раздражает или мешает в работе?",
            value=(
                "График поменяли без предупреждения на выходных, и непонятно,"
                " как считается премия."
            ),
        )

        submitted = st.form_submit_button(
            "Отправить ответы на анализ ИИ", type="primary"
        )

    if submitted:
        if not name or not q1:
            st.warning("Пожалуйста, заполните имя и хотя бы первый ответ.")
        else:
            with st.spinner("Нейросеть анализирует ответы..."):
                ai_res = analyze_with_ai(
                    api_key, name, department, role, days, q1, q2, q3
                )
                if ai_res:
                    new_emp = {
                        "id": len(st.session_state.employees) + 1,
                        "name": name,
                        "department": department,
                        "role": role,
                        "days": days,
                        "answers": {"q1": q1, "q2": q2, "q3": q3},
                        "ai_result": ai_res,
                        "bitrix_sent": False,
                    }
                    st.session_state.employees.append(new_emp)
                    st.success(
                        "✅ Опрос успешно обработан! Перейдите на вкладку «📊"
                        " Дашборд HR», чтобы увидеть результат."
                    )
                    st.json(ai_res)