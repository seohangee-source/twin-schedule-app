def render_mobile_calendar(df, month_input):
    year = month_input.year
    month = month_input.month

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdatescalendar(year, month)

    item_map = {}
    if not df.empty:
        temp = df.copy()
        temp["event_date_only"] = temp["event_date"].dt.date

        for _, row in temp.iterrows():
            d = row["event_date_only"]
            item_map.setdefault(d, []).append(row)

    st.markdown("""
    <style>
    .cal-wrap {
        width: 100%;
        overflow-x: auto;
    }
    .cal-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 4px;
        table-layout: fixed;
    }
    .cal-table th {
        font-size: 0.82rem;
        font-weight: 700;
        text-align: center;
        padding: 6px 0;
        color: #374151;
    }
    .cal-table td {
        vertical-align: top;
        height: 88px;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        background: #ffffff;
        padding: 4px;
    }
    .cal-other {
        background: #f9fafb !important;
        color: #9ca3af;
    }
    .cal-day {
        font-size: 0.78rem;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .cal-item {
        font-size: 0.62rem;
        line-height: 1.2;
        background: #eff6ff;
        color: #1d4ed8;
        border-radius: 6px;
        padding: 2px 4px;
        margin-bottom: 3px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .cal-item-child1 {
        background: #ffe4ec;
        color: #9f1239;
    }
    .cal-item-child2 {
        background: #dbeafe;
        color: #1d4ed8;
    }
    .cal-item-common {
        background: #dcfce7;
        color: #166534;
    }
    @media (max-width: 768px) {
        .cal-table th {
            font-size: 0.68rem;
            padding: 4px 0;
        }
        .cal-table td {
            height: 64px;
            padding: 3px;
        }
        .cal-day {
            font-size: 0.66rem;
            margin-bottom: 2px;
        }
        .cal-item {
            font-size: 0.52rem;
            padding: 1px 3px;
            border-radius: 4px;
            margin-bottom: 2px;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    html = []
    html.append("<div class='cal-wrap'>")
    html.append("<table class='cal-table'>")
    html.append("<thead><tr>")
    for w in ["월", "화", "수", "목", "금", "토", "일"]:
        html.append(f"<th>{w}</th>")
    html.append("</tr></thead><tbody>")

    for week in month_days:
        html.append("<tr>")
        for d in week:
            td_class = ""
            if d.month != month:
                td_class = "cal-other"

            html.append(f"<td class='{td_class}'>")
            html.append(f"<div class='cal-day'>{d.day}</div>")

            items = item_map.get(d, [])
            for item in items[:2]:
                twin = str(item.get("twin", "공통"))
                if twin == "첫째":
                    cls = "cal-item cal-item-child1"
                elif twin == "둘째":
                    cls = "cal-item cal-item-child2"
                else:
                    cls = "cal-item cal-item-common"

                title = str(item.get("title", ""))
                time_txt = str(item.get("event_time", ""))
                html.append(f"<div class='{cls}'>{time_txt} {title}</div>")

            if len(items) > 2:
                html.append(f"<div class='cal-item'>+{len(items)-2}건</div>")

            html.append("</td>")
        html.append("</tr>")
    html.append("</tbody></table></div>")

    st.markdown("".join(html), unsafe_allow_html=True)


def render_desktop_calendar(df, month_input):
    year = month_input.year
    month = month_input.month

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdatescalendar(year, month)

    item_map = {}
    if not df.empty:
        temp = df.copy()
        temp["event_date_only"] = temp["event_date"].dt.date
        for _, row in temp.iterrows():
            d = row["event_date_only"]
            item_map.setdefault(d, []).append(row)

    week_header = st.columns(7)
    for i, w in enumerate(["월", "화", "수", "목", "금", "토", "일"]):
        week_header[i].markdown(f"**{w}**")

    for week in month_days:
        cols = st.columns(7)
        for i, d in enumerate(week):
            with cols[i]:
                with st.container(border=True):
                    if d.month != month:
                        st.caption(d.day)
                    else:
                        st.write(f"**{d.day}**")

                    items = item_map.get(d, [])
                    for item in items[:3]:
                        twin = str(item.get("twin", "공통"))
                        title = str(item.get("title", ""))
                        time_txt = str(item.get("event_time", ""))

                        if twin == "첫째":
                            st.caption(f"🩷 {time_txt} {title}")
                        elif twin == "둘째":
                            st.caption(f"🩵 {time_txt} {title}")
                        else:
                            st.caption(f"💚 {time_txt} {title}")

                    if len(items) > 3:
                        st.caption(f"+{len(items)-3}건")