# streamlit_app.py
import streamlit as st
import pandas as pd
import altair as alt
import plotly.graph_objects as go

st.set_page_config(page_title="NBA Team Dashboard", layout="wide")

# =====================================================
# NBA HEADER
# =====================================================

nba_logo = "https://cdn.freebiesupply.com/logos/large/2x/nba-logo-png-transparent.png"

st.markdown(
    f"""
    <div style="display:flex; align-items:center; margin-bottom:15px;">
        <img src="{nba_logo}" width="70" style="margin-right:15px;">
        <h1 style="margin:0; padding:0;">
            NBA Dashboard
        </h1>
    </div>
    """,
    unsafe_allow_html=True,
)


# --- Season type selector (sidebar) ---
season_type = st.sidebar.selectbox(
    "Select Season Type",
    options=["Regular Season", "Playoffs"]
)

# --- Load the appropriate CSV based on selection ---
@st.cache_data
def load_data(season_type):
    if season_type == "Regular Season":
        return pd.read_csv("rs_clean.csv")
    else:
        return pd.read_csv("ps_clean.csv")

df = load_data(season_type)

# st.sidebar.title("Filters")
teams = sorted(df["team_display_name"].unique().tolist())
team = st.selectbox("Select Team", teams)

seasons = df["season"].dropna().drop_duplicates().sort_values().tolist()
# season = st.sidebar.selectbox("Season", seasons)

filtered = df[df['team_display_name'] == team].copy()

if filtered.empty:
    st.warning("No data available.")
    st.stop()

logo = filtered["team_logo"].iloc[0]
primary_color = "#" + str(filtered["team_color"].iloc[0]).zfill(6)
secondary_color = "#" + str(filtered["team_alternate_color"].iloc[0]).zfill(6)

# -----------------------------------------------------
# League Team PPG (remove duplicate player rows)
# -----------------------------------------------------

league_ppg = (
    df[
        ["game_id", "team_id", "team_score"]
    ]
    .drop_duplicates(subset=["game_id", "team_id"])
    ["team_score"]
    .mean()
)

st.markdown("### League Averages")

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Team PPG", f"{league_ppg:.1f}")
c2.metric("RPG", f"{df['rebounds'].mean():.1f}")
c3.metric("APG", f"{df['assists'].mean():.1f}")
c4.metric("SPG", f"{df['steals'].mean():.1f}")
c5.metric("BPG", f"{df['blocks'].mean():.1f}")


# -----------------------------------------------------
# Selected Team PPG
# -----------------------------------------------------

team_ppg = (
    filtered[
        ["game_id", "team_id", "team_score"]
    ]
    .drop_duplicates(subset=["game_id", "team_id"])
    ["team_score"]
    .mean()
)

st.subheader(f"📊 {team} - Team Averages")

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Team PPG", f"{team_ppg:.1f}")
c2.metric("RPG", f"{filtered['rebounds'].mean():.1f}")
c3.metric("APG", f"{filtered['assists'].mean():.1f}")
c4.metric("SPG", f"{filtered['steals'].mean():.1f}")
c5.metric("BPG", f"{filtered['blocks'].mean():.1f}")

st.divider()



# =====================================================
# NBA HEADER
# =====================================================
title_col, logo_col = st.columns([8,1])
with title_col:
    st.markdown(f"<h1 style='color:'white;'>{team.upper()}</h1>", unsafe_allow_html=True)
with logo_col:
    st.image(logo, width=90)

st.markdown(f"<div style='height:10px;background:linear-gradient(to right,{'white'});border-radius:5px;'></div>", unsafe_allow_html=True)


# =====================================================
# STARTING FIVE
# =====================================================
st.subheader("🏀 Starting Five")

starters = filtered[filtered["starter"] == True]

starting_five = (
    starters.groupby(
        [
            "athlete_display_name",
            "athlete_position_abbreviation",
            "athlete_headshot_href",
        ]
    )
    .agg(
        Starts=("starter", "sum"),
        PPG=("points", "mean"),
        RPG=("rebounds", "mean"),
        APG=("assists", "mean"),
    )
    .reset_index()
    .sort_values("Starts", ascending=False)
    .head(5)
)

cols = st.columns(5)

for (_, player), col in zip(starting_five.iterrows(), cols):

    with col:

        st.image(player["athlete_headshot_href"], width=95)

        st.markdown(
            f"**{player['athlete_display_name']} ({player['athlete_position_abbreviation']})**"
        )

        st.caption(
            f"PPG {player['PPG']:.1f} • RPG {player['RPG']:.1f} • APG {player['APG']:.1f}"
        )

# =====================================================
# HOME VS AWAY + POSITION STATS (COORDINATED VIEWS)
# =====================================================

st.subheader("📊 Average Stats per Player by Position")

# ----------------------------------------
# Selection (Donut controls Bar Chart)
# ----------------------------------------

location_select = alt.selection_point(
    fields=["Location"],
    empty=True
)

# ----------------------------------------
# Prepare Position Data
# ----------------------------------------

pos = filtered[
    filtered["athlete_position_name"].isin(
        ["Guard", "Forward", "Center"]
    )
].copy()

pos["Location"] = pos["home_away"].str.title()

# Convert to long format
pos = pos.melt(
    id_vars=["athlete_position_name", "Location"],
    value_vars=[
        "points",
        "assists",
        "offensive_rebounds",
        "blocks",
        "defensive_rebounds",
        "steals",
    ],
    var_name="metric",
    value_name="value",
)

# Pretty metric names
pos["Metric"] = pos["metric"].map({
    "points": "Points",
    "assists": "Assists",
    "offensive_rebounds": "Off. Rebounds",
    "blocks": "Blocks",
    "defensive_rebounds": "Def. Rebounds",
    "steals": "Steals",
})

# ----------------------------------------
# Home vs Away Wins (Donut)
# ----------------------------------------

wins = filtered[filtered["team_winner"] == True]

home = (wins["home_away"] == "home").sum()
away = (wins["home_away"] == "away").sum()

wr = pd.DataFrame({
    "Location": ["Home", "Away"],
    "Wins": [home, away]
})

donut = (
    alt.Chart(wr)
    .mark_arc(innerRadius=70)
    .encode(
        theta=alt.Theta("Wins:Q"),
        color=alt.condition(
            location_select,
            alt.Color(
                "Location:N",
                scale=alt.Scale(
                    domain=["Home", "Away"],
                    range=["red", "blue"]
                ),
                legend=alt.Legend(title="Location")
            ),
            alt.value("#D3D3D3")
        ),
        tooltip=[
            alt.Tooltip("Location:N"),
            alt.Tooltip("Wins:Q", title="Wins")
        ]
    )
    .add_params(location_select)
    .properties(
        width=300,
        height=300,
        title=f"{team} Home vs. Away Wins"
    )
)

# ----------------------------------------
# Average Stats by Position (Filtered)
# ----------------------------------------

bars = (
    alt.Chart(pos)
    .transform_filter(location_select)
    .transform_aggregate(
        value="mean(value)",
        groupby=[
            "athlete_position_name",
            "Metric",
            "Location",
        ],
    )
    .mark_bar(
        cornerRadiusTopLeft=3,
        cornerRadiusTopRight=3,
    )
    .encode(
        x=alt.X(
            "athlete_position_name:N",
            title=None,
            sort=["Guard", "Forward", "Center"],
        ),
        y=alt.Y(
            "value:Q",
            title="Average per Player per Game",
        ),
        color=alt.Color(
            "athlete_position_name:N",
            scale=alt.Scale(
            domain=["Guard", "Forward", "Center"],
            range=[
                "red",
                "blue",
                "#B5B5B5",
            ],
            ),
            legend=None,
            
        ),
        column=alt.Column(
            "Metric:N",
            sort=[
                "Points",
                "Assists",
                "Off. Rebounds",
                "Blocks",
                "Def. Rebounds",
                "Steals",
            ],
            title=None,
        ),
        tooltip=[
            alt.Tooltip(
                "athlete_position_name:N",
                title="Position"
            ),
            alt.Tooltip("Location:N"),
            alt.Tooltip("Metric:N"),
            alt.Tooltip(
                "value:Q",
                title="Average",
                format=".2f"
            ),
        ],
    )
    .properties(
        width=110,
        height=300,
        title=f"{team} Average Stats by Position"
    )
)

# ----------------------------------------
# Display Coordinated Visualization
# ----------------------------------------

combined = alt.hconcat(donut, bars).resolve_scale(color="independent")

st.altair_chart(combined, use_container_width=True)


# =====================================================
# PLAYER VS TEAM PERFORMANCE
# =====================================================

st.divider()
st.header("Individual Player Performance 🏀")
st.subheader("How do player compare to their counterparts?")
st.caption(f"Select a player from {team.title()} and compare their perfromacne metrics against the league and their team.")

# ---------------- Select Player ----------------

players = (
    filtered["athlete_display_name"]
    .dropna()
    .drop_duplicates()
    .sort_values()
    .tolist()
)

left, right = st.columns([1, 2])

with left:

    player = st.selectbox(
        "Select Player",
        players,
        key="player_compare"
    )


# ---------------- Player Data ----------------

player_df = filtered[
    filtered["athlete_display_name"] == player
]

player_photo = player_df["athlete_headshot_href"].iloc[0]
player_position = player_df["athlete_position_abbreviation"].mode().iloc[0]

player_stats = {
    "3PT%": (
        player_df["three_point_field_goals_made"].sum()
        / player_df["three_point_field_goals_attempted"].sum() * 100
        if player_df["three_point_field_goals_attempted"].sum() > 0 else 0
    ),
    "FG%": (
        player_df["field_goals_made"].sum()
        / player_df["field_goals_attempted"].sum() * 100
        if player_df["field_goals_attempted"].sum() > 0 else 0
    ),
    "Blocks": player_df["blocks"].mean(),
    "Steals": player_df["steals"].mean(),
    "Assists": player_df["assists"].mean(),
    "Rebounds": player_df["rebounds"].mean(),
    "Points": player_df["points"].mean(),
}

# ---------------- Team Data ----------------

team_stats = {
    "3PT%": (
        filtered["three_point_field_goals_made"].sum()
        / filtered["three_point_field_goals_attempted"].sum() * 100
        if filtered["three_point_field_goals_attempted"].sum() > 0 else 0
    ),
    "FG%": (
        filtered["field_goals_made"].sum()
        / filtered["field_goals_attempted"].sum() * 100
        if filtered["field_goals_attempted"].sum() > 0 else 0
    ),
    "Blocks": filtered["blocks"].mean(),
    "Steals": filtered["steals"].mean(),
    "Assists": filtered["assists"].mean(),
    "Rebounds": filtered["rebounds"].mean(),
    "Points": filtered["points"].mean(),
}

# ---------------- NBA Data ----------------

nba_stats = {
    "3PT%": (
        df["three_point_field_goals_made"].sum()
        / df["three_point_field_goals_attempted"].sum() * 100
        if df["three_point_field_goals_attempted"].sum() > 0 else 0
    ),
    "FG%": (
        df["field_goals_made"].sum()
        / df["field_goals_attempted"].sum() * 100
        if df["field_goals_attempted"].sum() > 0 else 0
    ),
    "Blocks": df["blocks"].mean(),
    "Steals": df["steals"].mean(),
    "Assists": df["assists"].mean(),
    "Rebounds": df["rebounds"].mean(),
    "Points": df["points"].mean(),
}

# MAX VALUES FOR NORMALIZATION (TEAM + SEASON)

player_avgs = (
    filtered.groupby("athlete_display_name")
    .agg(
        Points=("points", "mean"),
        Rebounds=("rebounds", "mean"),
        Assists=("assists", "mean"),
        Steals=("steals", "mean"),
        Blocks=("blocks", "mean"),
        FG_Made=("field_goals_made", "sum"),
        FG_Att=("field_goals_attempted", "sum"),
        Three_Made=("three_point_field_goals_made", "sum"),
        Three_Att=("three_point_field_goals_attempted", "sum"),
    )
)

player_avgs["FG%"] = (
    player_avgs["FG_Made"] / player_avgs["FG_Att"] * 100
).fillna(0)

player_avgs["3PT%"] = (
    player_avgs["Three_Made"] / player_avgs["Three_Att"] * 100
).fillna(0)

max_values = {
    "3PT%": player_avgs["3PT%"].max(),
    "FG%": player_avgs["FG%"].max(),
    "Blocks": player_avgs["Blocks"].max(),
    "Steals": player_avgs["Steals"].max(),
    "Assists": player_avgs["Assists"].max(),
    "Rebounds": player_avgs["Rebounds"].max(),
    "Points": player_avgs["Points"].max(),
}
### NORMALIZE DATA FOR SPIDER RADAR

def normalize(player_stats, team_stats, nba_stats, max_values):

    player_norm = {}
    team_norm = {}
    nba_norm = {}

    for metric in player_stats:

        max_val = max_values[metric]

        if max_val == 0:
            player_norm[metric] = 0
            team_norm[metric] = 0
            nba_norm[metric] = 0
        else:
            player_norm[metric] = player_stats[metric] / max_val * 100
            team_norm[metric] = team_stats[metric] / max_val * 100
            nba_norm[metric] = nba_stats[metric] / max_val * 100

    return player_norm, team_norm, nba_norm

player_norm, team_norm, nba_norm = normalize(player_stats, team_stats, nba_stats, max_values)

categories = list(player_stats.keys())

# Close the radar polygons
player_values = list(player_norm.values())
player_values.append(player_values[0])

team_values = list(team_norm.values())
team_values.append(team_values[0])

nba_values = list(nba_norm.values())
nba_values.append(nba_values[0])

categories_closed = categories + [categories[0]]

left, right = st.columns([1, 2])

with right:

    player_df = filtered[
        filtered["athlete_display_name"] == player
    ]

    player_photo = player_df["athlete_headshot_href"].iloc[0]
    player_position = player_df["athlete_position_abbreviation"].mode().iloc[0]
    player_number = player_df["athlete_jersey"].iloc[0]

    st.image(player_photo, width=375)
    st.caption(f"{player} • {player_position} • Jersey #{player_number:.0f}")

with left:

    fig = go.Figure()
    # NBA Average
    fig.add_trace(
        go.Scatterpolar(
            r=nba_values,
            theta=categories_closed,
            fill="toself",
            name="NBA Average",
            line=dict(color="#808080", width=2, dash="dot"),
            opacity=0.55
        )
    )
    # Team
    fig.add_trace(
        go.Scatterpolar(
            r=team_values,
            theta=categories_closed,
            fill="toself",
            name="Team Average",
            line=dict(color='red'),
            opacity=0.45
        )
    )

    # Player
    fig.add_trace(
        go.Scatterpolar(
            r=player_values,
            theta=categories_closed,
            fill="toself",
            name=player,
            line=dict(color='blue', width=3),
            opacity=0.75
        )
    )


    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True
            )
        ),
        legend=dict(
            orientation="v",
            x=1.05,
            y=0.5,
            xanchor="left",
            yanchor="middle",
            font=dict(size=12)
        ),
        margin=dict(l=30, r=30, t=20, b=20),
        height=300
    )

    st.plotly_chart(fig, use_container_width=True)