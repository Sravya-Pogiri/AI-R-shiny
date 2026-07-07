# R Shiny Agent Knowledge Base

> This document serves as the core knowledge base for the R Shiny AI Agent. The agent should reference the patterns, conventions, and best practices described here when generating, reviewing, or debugging Shiny code.

---

## Table of Contents

1. [Shiny Core Architecture](#1-shiny-core-architecture)
2. [Project Structure Conventions](#2-project-structure-conventions)
3. [UI Layer: Layout & Components](#3-ui-layer-layout--components)
4. [Server Layer: Reactive Programming Model](#4-server-layer-reactive-programming-model)
5. [Modular Development](#5-modular-development)
6. [Data Handling & Performance Optimization](#6-data-handling--performance-optimization)
7. [Visualization Best Practices](#7-visualization-best-practices)
8. [Tables & Data Display](#8-tables--data-display)
9. [User Experience Enhancements](#9-user-experience-enhancements)
10. [Error Handling & Debugging](#10-error-handling--debugging)
11. [Testing Strategy](#11-testing-strategy)
12. [Deployment & Production](#12-deployment--production)
13. [Security](#13-security)
14. [Common Anti-Patterns & Pitfalls](#14-common-anti-patterns--pitfalls)
15. [Package Quick Reference](#15-package-quick-reference)
16. [Code Template Library](#16-code-template-library)

---

## 1. Shiny Core Architecture

### 1.1 The Three Components of a Shiny App

```r
library(shiny)

ui <- fluidPage(
  # UI definition: what the user sees
)

server <- function(input, output, session) {
  # Server logic: how data flows
}

shinyApp(ui = ui, server = server)
```

### 1.2 Reactive Execution Model

Shiny's core is **reactive programming**. Understanding the execution model is fundamental to writing effective Shiny apps:

- **Reactive Source**: `input$xxx` — user actions trigger changes
- **Reactive Conductor**: `reactive()`, `reactiveVal()`, `reactiveValues()` — intermediate computation layer
- **Reactive Endpoint**: `observe()`, `observeEvent()`, `render*()` — produce side effects or outputs

**Execution Rules:**

- Reactive expressions are **lazy**: they only execute when demanded by a downstream consumer
- Observers are **eager**: they execute immediately when their dependencies change
- `invalidateLater()` creates time-based refresh cycles
- A reactive expression's result is **cached** until its dependencies are invalidated

**Dependency Tracking:**

```r
# Shiny automatically tracks which reactive values are read inside a reactive expression
# No manual dependency declaration is needed
filtered_data <- reactive({
  # Shiny knows this expression depends on input$species and input$min_length
  iris |>
    dplyr::filter(Species == input$species) |>
    dplyr::filter(Sepal.Length >= input$min_length)
})
```

### 1.3 Session Lifecycle

```r
server <- function(input, output, session) {
  # session$onSessionEnded — fires when the user closes the browser tab
  session$onSessionEnded(function() {
    # Clean up database connections, temp files, etc.
    dbDisconnect(con)
  })

  # session$onFlushed — fires after outputs are sent to the browser
  # session$onFlush  — fires before outputs are sent to the browser
}
```

---

## 2. Project Structure Conventions

### 2.1 Small Apps (Single File)

Best for prototypes and simple applications:

```
my-app/
├── app.R              # Contains ui + server + shinyApp()
├── data/              # Static data files
│   └── dataset.csv
└── www/               # Static assets (CSS, JS, images)
    ├── style.css
    └── logo.png
```

### 2.2 Medium Apps (Multi-File)

```
my-app/
├── ui.R               # UI definition
├── server.R           # Server logic
├── global.R           # Global objects (load packages, read data, define constants)
├── R/                 # Helper functions and modules
│   ├── mod_sidebar.R
│   ├── mod_table.R
│   └── utils.R
├── data/
├── tests/
│   └── testthat/
└── www/
```

**Important:** `global.R` executes once at app startup (shared across all sessions). Code inside `server.R` executes once per session. Place immutable data loading in `global.R`.

### 2.3 Large Apps (golem Framework)

```
myapp/
├── DESCRIPTION             # R package metadata
├── NAMESPACE
├── R/
│   ├── app_config.R        # App configuration
│   ├── app_server.R        # Main server
│   ├── app_ui.R            # Main UI
│   ├── mod_dashboard.R     # Module: dashboard
│   ├── mod_analysis.R      # Module: analysis
│   ├── fct_helpers.R       # Business logic functions (non-reactive)
│   └── utils_formatting.R  # Utility functions
├── inst/
│   ├── app/www/            # Static assets
│   └── golem-config.yml    # Environment configuration
├── tests/
│   └── testthat/
├── dev/
│   ├── 01_start.R
│   ├── 02_dev.R
│   └── 03_deploy.R
└── data-raw/               # Data preprocessing scripts
```

### 2.4 File Naming Conventions

```
R/
├── mod_xxx_ui.R / mod_xxx_server.R    # Module files (or combined as mod_xxx.R)
├── fct_xxx.R                           # Business functions (pure, non-reactive)
├── utils_xxx.R                         # Utility functions (formatting, conversion)
├── app_ui.R                            # Main UI assembly
└── app_server.R                        # Main server assembly
```

---

## 3. UI Layer: Layout & Components

### 3.1 Modern Layout: bslib (Recommended)

bslib is the officially recommended modern UI framework for Shiny, built on Bootstrap 5:

```r
library(bslib)

ui <- page_sidebar(
  title = "My Application",
  theme = bs_theme(
    version = 5,
    bootswatch = "flatly",       # Preset theme
    primary = "#0054AD",          # Custom primary color
    "navbar-bg" = "#0054AD"
  ),
  sidebar = sidebar(
    title = "Filters",
    width = 300,
    selectInput("species", "Species", choices = c("setosa", "versicolor", "virginica")),
    sliderInput("n", "Sample Size", min = 1, max = 150, value = 50)
  ),
  # Main content area
  navset_card_tab(
    nav_panel("Overview", plotOutput("overview_plot")),
    nav_panel("Data", DT::dataTableOutput("data_table")),
    nav_panel("Analysis", uiOutput("analysis_ui"))
  )
)
```

**bslib Layout Components:**

```r
# Page-level layouts
page_sidebar()      # Page with sidebar (most common)
page_navbar()       # Top navigation bar page
page_fillable()     # Fill the browser window
page_fluid()        # Fluid layout page

# Cards
card(
  card_header("Title"),
  card_body(plotOutput("plot1")),
  card_footer("Notes"),
  full_screen = TRUE   # Allow fullscreen toggle
)

# Multi-column layout
layout_columns(
  col_widths = c(4, 8),  # 12-column grid system
  card(...),
  card(...)
)

# Responsive columns (auto-wrap)
layout_column_wrap(
  width = "250px",  # Minimum width per column
  card(...),
  card(...),
  card(...)
)

# Value boxes for KPIs
value_box(
  title = "Total Revenue",
  value = textOutput("total_sales"),
  showcase = bsicons::bs_icon("currency-dollar"),
  theme = "primary"
)
```

### 3.2 Traditional Layout: shinydashboard

Still widely used, suitable for admin-panel style interfaces:

```r
library(shinydashboard)

ui <- dashboardPage(
  dashboardHeader(title = "Dashboard"),
  dashboardSidebar(
    sidebarMenu(
      menuItem("Dashboard", tabName = "dashboard", icon = icon("dashboard")),
      menuItem("Reports", tabName = "report", icon = icon("chart-bar"))
    )
  ),
  dashboardBody(
    tabItems(
      tabItem(tabName = "dashboard",
        fluidRow(
          box(width = 6, plotOutput("plot1")),
          box(width = 6, plotOutput("plot2"))
        )
      ),
      tabItem(tabName = "report",
        DT::dataTableOutput("report_table")
      )
    )
  )
)
```

### 3.3 Input Components Quick Reference

```r
# Text inputs
textInput("id", "Label", value = "default")
textAreaInput("id", "Label", rows = 5)
passwordInput("id", "Password")

# Numeric inputs
numericInput("id", "Label", value = 10, min = 0, max = 100, step = 1)
sliderInput("id", "Label", min = 0, max = 100, value = 50)
sliderInput("id", "Range", min = 0, max = 100, value = c(25, 75))  # Dual slider

# Selection inputs
selectInput("id", "Label", choices = c("A", "B", "C"), multiple = FALSE)
selectizeInput("id", "Label", choices = NULL, multiple = TRUE,
               options = list(maxItems = 5, placeholder = "Type to search..."))
radioButtons("id", "Label", choices = c("Option A" = "a", "Option B" = "b"))
checkboxGroupInput("id", "Label", choices = c("X", "Y", "Z"))
checkboxInput("id", "Enable?", value = TRUE)

# Date inputs
dateInput("id", "Date", value = Sys.Date())
dateRangeInput("id", "Date Range", start = Sys.Date() - 30, end = Sys.Date())

# File input
fileInput("id", "Upload File", accept = c(".csv", ".xlsx"),
          multiple = FALSE, buttonLabel = "Browse...", placeholder = "No file selected")

# Buttons
actionButton("id", "Run", icon = icon("play"), class = "btn-primary")
downloadButton("id", "Download Report")
```

> [!IMPORTANT]
> **Input Help Text:** Shiny input components (like `numericInput()`, `selectInput()`, etc.) **do not** accept a `help` parameter. To include help or descriptive text, you must use a separate `helpText("message")` element immediately below the input component.

### 3.4 Dynamic UI

```r
# Method 1: renderUI / uiOutput (fully dynamic)
output$dynamic_controls <- renderUI({
  req(input$dataset)
  cols <- names(get_data(input$dataset))
  selectInput("column", "Select Column", choices = cols)
})

# Method 2: updateXxxInput (more efficient — updates value only)
observeEvent(input$dataset, {
  cols <- names(get_data(input$dataset))
  updateSelectInput(session, "column", choices = cols)
})

# Method 3: conditionalPanel (client-side, no server round-trip)
conditionalPanel(
  condition = "input.show_advanced == true",
  numericInput("threshold", "Threshold", value = 0.05)
)

# Method 4: insertUI / removeUI (add/remove UI elements)
observeEvent(input$add_filter, {
  id <- paste0("filter_", input$add_filter)
  insertUI(
    selector = "#filter_container",
    where = "beforeEnd",
    ui = div(id = id, selectInput(NS(id, "var"), "Variable", choices = col_names))
  )
})
```

**Selection Principle:** `updateXxxInput` > `conditionalPanel` > `renderUI` (performance decreases in that order)

---

## 4. Server Layer: Reactive Programming Model

### 4.1 reactive() — Reactive Computations

```r
# Use for: computations whose results should be cached (data filtering, model fitting, etc.)
filtered_data <- reactive({
  req(input$species)  # Ensure input is valid
  iris |> dplyr::filter(Species == input$species)
})

# Call with parentheses when consuming the value
output$plot <- renderPlot({
  ggplot(filtered_data(), aes(x = Sepal.Length, y = Sepal.Width)) +
    geom_point()
})
```

### 4.2 reactiveVal() and reactiveValues() — Mutable State

```r
# reactiveVal: single mutable value
counter <- reactiveVal(0)
observeEvent(input$increment, {
  counter(counter() + 1)   # Read: counter()  Write: counter(new_value)
})

# reactiveValues: container for multiple mutable values
state <- reactiveValues(
  data = NULL,
  selected_rows = integer(0),
  last_updated = Sys.time()
)
observeEvent(input$load, {
  state$data <- read.csv(input$file$datapath)
  state$last_updated <- Sys.time()
})
```

**Selection Principle:** Use `reactiveVal()` for a single value, `reactiveValues()` for multiple related state variables.

### 4.3 observe() vs observeEvent() — Side Effects

```r
# observe: triggers whenever ANY dependency changes (use sparingly — easy to over-trigger)
observe({
  # Executes whenever input$x OR input$y changes
  message("x = ", input$x, ", y = ", input$y)
})

# observeEvent: triggers only on a specific event (recommended)
observeEvent(input$submit, {
  # Executes only when the submit button is clicked
  result <- run_analysis(filtered_data())
  state$result <- result
  showNotification("Analysis complete!", type = "message")
}, ignoreNULL = TRUE, ignoreInit = TRUE)

# Key parameters:
# ignoreNULL = TRUE  — ignore NULL values (default TRUE)
# ignoreInit = TRUE  — do not trigger on app startup (default TRUE for observeEvent)
# once = TRUE        — trigger only once
# priority = 10      — execution priority (higher number = executed first)
```

### 4.4 eventReactive() — Event-Driven Reactive Values

```r
# Recomputes only when the button is clicked, not when inputs change
analysis_result <- eventReactive(input$run_analysis, {
  req(filtered_data())
  run_model(filtered_data(), method = input$method)
})
```

### 4.5 isolate() — Break Dependency Links

```r
output$summary <- renderText({
  # Depends on input$update_btn, but reads input$text without creating a dependency
  input$update_btn
  isolate({
    paste("Current text:", input$text)
  })
})
```

### 4.6 req() and validate() — Input Validation

```r
output$plot <- renderPlot({
  # req: silently stops execution (no error displayed)
  req(input$file)                    # Ensure file is uploaded
  req(input$n > 0)                   # Ensure condition is met
  req(nrow(filtered_data()) > 0,
      cancelOutput = TRUE)           # cancelOutput preserves previous output

  # validate + need: display user-friendly error messages
  validate(
    need(input$species != "", "Please select a species"),
    need(nrow(filtered_data()) > 0, "No data after filtering. Adjust your criteria."),
    need(is.numeric(input$n), "Please enter a valid number")
  )

  # Proceed with rendering after validation passes
  ggplot(filtered_data(), aes(x = Sepal.Length)) + geom_histogram()
})
```

### 4.7 Reactive Chain Design Pattern

```r
server <- function(input, output, session) {

  # Layer 1: Data loading
  raw_data <- reactive({
    req(input$file)
    ext <- tools::file_ext(input$file$name)
    switch(ext,
      csv = readr::read_csv(input$file$datapath),
      xlsx = readxl::read_excel(input$file$datapath),
      validate("Unsupported file format")
    )
  })

  # Layer 2: Data cleaning (depends on raw_data)
  clean_data <- reactive({
    raw_data() |>
      dplyr::mutate(across(where(is.character), trimws)) |>
      tidyr::drop_na()
  })

  # Layer 3: Data filtering (depends on clean_data + inputs)
  filtered_data <- reactive({
    req(input$date_range)
    clean_data() |>
      dplyr::filter(
        date >= input$date_range[1],
        date <= input$date_range[2]
      )
  })

  # Endpoint layer: Outputs (depend on filtered_data)
  output$plot <- renderPlot({ ggplot(filtered_data(), ...) })
  output$table <- DT::renderDataTable({ filtered_data() })
  output$summary <- renderPrint({ summary(filtered_data()) })
}
```

---

## 5. Modular Development

### 5.1 Why Modularize

- **Namespace isolation**: prevents input/output ID collisions
- **Code reuse**: the same module can be instantiated multiple times
- **Testability**: modules can be tested in isolation
- **Collaborative development**: different developers own different modules

### 5.2 Basic Module Structure

```r
# R/mod_data_filter.R

# ---- UI Function ----
mod_data_filter_ui <- function(id) {
  ns <- NS(id)  # Create namespace function
  tagList(
    selectInput(ns("variable"), "Select Variable", choices = NULL),
    sliderInput(ns("range"), "Range", min = 0, max = 100, value = c(0, 100)),
    actionButton(ns("apply"), "Apply Filter", class = "btn-primary")
  )
}

# ---- Server Function ----
mod_data_filter_server <- function(id, data) {
  # data parameter is a reactive expression passed from the parent
  moduleServer(id, function(input, output, session) {
    ns <- session$ns  # Get ns in server context (for dynamic UI)

    # Update UI when data changes
    observe({
      req(data())
      numeric_cols <- names(dplyr::select(data(), where(is.numeric)))
      updateSelectInput(session, "variable", choices = numeric_cols)
    })

    # Update slider range
    observe({
      req(data(), input$variable)
      col_data <- data()[[input$variable]]
      updateSliderInput(session, "range",
        min = floor(min(col_data, na.rm = TRUE)),
        max = ceiling(max(col_data, na.rm = TRUE)),
        value = range(col_data, na.rm = TRUE)
      )
    })

    # Return filtered data (reactive)
    filtered <- eventReactive(input$apply, {
      req(data(), input$variable, input$range)
      data() |>
        dplyr::filter(
          .data[[input$variable]] >= input$range[1],
          .data[[input$variable]] <= input$range[2]
        )
    }, ignoreNULL = FALSE)

    return(filtered)
  })
}
```

### 5.3 Module Invocation

```r
# app_ui.R
ui <- page_sidebar(
  sidebar = sidebar(
    mod_data_filter_ui("filter1"),    # Instance 1
    mod_data_filter_ui("filter2")     # Instance 2 (reusable)
  ),
  card(DT::dataTableOutput("result"))
)

# app_server.R
server <- function(input, output, session) {
  raw_data <- reactive({ iris })

  # Modules return reactives — they can be chained
  filtered1 <- mod_data_filter_server("filter1", data = raw_data)
  filtered2 <- mod_data_filter_server("filter2", data = filtered1)

  output$result <- DT::renderDataTable({ filtered2() })
}
```

### 5.4 Inter-Module Communication Patterns

```r
# Pattern 1: Via return values (recommended)
# Module A returns a reactive, Module B receives it
result_a <- mod_a_server("a")
mod_b_server("b", data = result_a)

# Pattern 2: Via shared reactiveValues
shared_state <- reactiveValues(selected = NULL, filters = list())
mod_a_server("a", state = shared_state)
mod_b_server("b", state = shared_state)

# Pattern 3: Via session$userData (global sharing — use sparingly)
session$userData$shared <- reactiveValues(...)
```

### 5.5 Returning Multiple Values from a Module

```r
mod_analysis_server <- function(id, data) {
  moduleServer(id, function(input, output, session) {
    result <- reactive({ ... })
    summary_text <- reactive({ ... })

    # Return a named list
    list(
      result = result,
      summary = summary_text,
      is_valid = reactive({ !is.null(result()) })
    )
  })
}

# Caller side
analysis <- mod_analysis_server("analysis", data = filtered_data)
output$result_table <- DT::renderDataTable({ analysis$result() })
output$summary <- renderText({ analysis$summary() })
```

---

## 6. Data Handling & Performance Optimization

### 6.1 Data Loading Strategy

```r
# global.R — load immutable data here (shared across all sessions, loaded once)
library(dplyr)
library(ggplot2)

# Preload static data
lookup_table <- readr::read_csv("data/lookup.csv")
model_params <- readRDS("data/model.rds")

# Database connection pool (shared across sessions)
library(pool)
pool <- dbPool(
  drv = RPostgres::Postgres(),
  dbname = "mydb",
  host = "localhost",
  user = Sys.getenv("DB_USER"),
  password = Sys.getenv("DB_PASS"),
  minSize = 2,
  maxSize = 10
)
onStop(function() { poolClose(pool) })

# server.R — query on demand
server <- function(input, output, session) {
  user_data <- reactive({
    pool |>
      tbl("sales") |>
      filter(region == !!input$region) |>
      collect()  # Filter on DB side, pull only what's needed
  })
}
```

### 6.2 File Upload Handling

```r
server <- function(input, output, session) {
  uploaded_data <- reactive({
    req(input$file)

    ext <- tools::file_ext(input$file$name)

    tryCatch({
      data <- switch(ext,
        csv  = readr::read_csv(input$file$datapath, show_col_types = FALSE),
        tsv  = readr::read_tsv(input$file$datapath, show_col_types = FALSE),
        xlsx = readxl::read_excel(input$file$datapath),
        xls  = readxl::read_excel(input$file$datapath),
        rds  = readRDS(input$file$datapath),
        sas7bdat = haven::read_sas(input$file$datapath),
        {
          showNotification(paste("Unsupported format:", ext), type = "error")
          return(NULL)
        }
      )
      showNotification(
        paste("Loaded", nrow(data), "rows x", ncol(data), "columns"),
        type = "message"
      )
      data
    }, error = function(e) {
      showNotification(paste("Read failed:", e$message), type = "error")
      NULL
    })
  })
}
```

### 6.3 Performance Optimization Techniques

```r
# 1. bindCache: cache render output (Shiny >= 1.6)
output$plot <- renderPlot({
  ggplot(filtered_data(), aes(x = x, y = y)) + geom_point()
}) |> bindCache(input$species, input$n)
# Same input parameters return cached output without re-rendering

# 2. bindEvent: pipe-style alternative to eventReactive
filtered <- reactive({
  iris |> filter(Species == input$species)
}) |> bindEvent(input$apply)
# Equivalent to eventReactive(input$apply, { ... })

# 3. debounce / throttle: control trigger frequency
search_term <- reactive({ input$search }) |> debounce(500)
# Triggers downstream computation 500ms after user stops typing
# throttle(1000) — triggers at most once per 1000ms

# 4. Large data lazy loading
output$big_table <- DT::renderDataTable({
  DT::datatable(
    big_data(),
    options = list(
      processing = TRUE,
      serverSide = TRUE,   # Server-side pagination
      pageLength = 25
    )
  )
})

# 5. Progress indicators (long-running operations)
observeEvent(input$run, {
  withProgress(message = "Analyzing...", value = 0, {
    for (i in seq_len(10)) {
      incProgress(1/10, detail = paste("Step", i))
      Sys.sleep(0.5)
    }
  })
})

# 6. Async processing (non-blocking for other users)
library(promises)
library(future)
plan(multisession)

output$async_result <- renderTable({
  future_promise({
    # This code runs in a background process
    Sys.sleep(10)  # Simulate expensive operation
    heavy_computation()
  })
})
```

---

## 7. Visualization Best Practices

### 7.1 ggplot2 — Static Plots (renderPlot)

```r
output$gg_plot <- renderPlot({
  req(filtered_data())

  p <- ggplot(filtered_data(), aes(x = .data[[input$x_var]], y = .data[[input$y_var]])) +
    geom_point(aes(color = .data[[input$color_var]]), alpha = 0.7, size = 2) +
    geom_smooth(method = "lm", se = TRUE, color = "steelblue") +
    labs(
      title = paste(input$y_var, "vs", input$x_var),
      x = input$x_var,
      y = input$y_var,
      color = input$color_var
    ) +
    theme_minimal(base_size = 14) +
    theme(
      plot.title = element_text(face = "bold"),
      legend.position = "bottom"
    )

  print(p)
}, res = 96)  # res controls DPI
```

**Note on `.data[[]]` pronoun**: When selecting columns by variable name in Shiny, use `.data[[var]]` instead of `aes_string()` (deprecated).

### 7.2 plotly — Interactive Charts (renderPlotly)

```r
library(plotly)

# Method 1: ggplotly conversion
output$interactive_plot <- renderPlotly({
  p <- ggplot(filtered_data(), aes(x = x, y = y, text = paste("ID:", id))) +
    geom_point()

  ggplotly(p, tooltip = "text") |>
    layout(
      hoverlabel = list(bgcolor = "white"),
      dragmode = "select"    # Enable box selection
    ) |>
    config(displayModeBar = TRUE, displaylogo = FALSE)
})

# Method 2: Native plotly (better performance, more customizable)
output$native_plotly <- renderPlotly({
  plot_ly(
    data = filtered_data(),
    x = ~date, y = ~value, color = ~category,
    type = "scatter", mode = "lines+markers",
    hovertemplate = "%{x}<br>Value: %{y:.2f}<extra>%{fullData.name}</extra>"
  ) |>
    layout(
      xaxis = list(title = "Date", rangeslider = list(visible = TRUE)),
      yaxis = list(title = "Value"),
      legend = list(orientation = "h", y = -0.2)
    )
})

# Capturing plotly events
observeEvent(event_data("plotly_click"), {
  click_info <- event_data("plotly_click")
  state$selected_point <- click_info$pointNumber
})

observeEvent(event_data("plotly_selected"), {
  selected <- event_data("plotly_selected")
  state$selected_rows <- selected$pointNumber
})
```

### 7.3 echarts4r — Dynamic Charts

```r
library(echarts4r)

output$echart <- renderEcharts4r({
  filtered_data() |>
    e_charts(x = date) |>
    e_line(value, smooth = TRUE) |>
    e_area(value, smooth = TRUE) |>
    e_tooltip(trigger = "axis") |>
    e_datazoom(type = "slider") |>
    e_theme("walden")
})
```

### 7.4 Chart Selection Guide

| Scenario | Recommended | Rationale |
|----------|-------------|-----------|
| Quick prototyping / reports | ggplot2 | Rich ecosystem, consistent grammar |
| Needs interaction (hover/zoom/select) | plotly | Comprehensive event system |
| Large data volume (>10k points) | echarts4r or native plotly | Canvas rendering is faster |
| Geospatial visualization | leaflet | Most mature Shiny integration |
| Real-time dashboards | echarts4r | Best animation and live update support |
| Network / relationship graphs | visNetwork | Interactive network diagrams |
| Time series | dygraphs | Purpose-built for time series |

---

## 8. Tables & Data Display

### 8.1 DT (DataTables)

```r
output$data_table <- DT::renderDataTable({
  DT::datatable(
    filtered_data(),
    options = list(
      pageLength = 25,
      scrollX = TRUE,           # Horizontal scrolling
      scrollY = "400px",        # Fixed height
      searching = TRUE,
      order = list(list(0, "desc")),
      columnDefs = list(
        list(className = "dt-center", targets = "_all"),
        list(visible = FALSE, targets = c(0))  # Hide first column
      )
    ),
    selection = list(mode = "multiple", target = "row"),
    filter = "top",             # Column filters
    rownames = FALSE,
    class = "compact stripe hover"
  ) |>
    DT::formatCurrency("revenue", currency = "$", digits = 0) |>
    DT::formatPercentage("growth_rate", digits = 1) |>
    DT::formatDate("date", method = "toLocaleDateString") |>
    DT::formatStyle("status",
      backgroundColor = DT::styleEqual(
        c("Normal", "Warning", "Critical"),
        c("#d4edda", "#fff3cd", "#f8d7da")
      )
    )
})

# Get selected rows
observeEvent(input$data_table_rows_selected, {
  selected <- filtered_data()[input$data_table_rows_selected, ]
  state$selected_items <- selected
})

# DT proxy: manipulate the table without full re-render
proxy <- DT::dataTableProxy("data_table")
observeEvent(input$clear_selection, {
  DT::selectRows(proxy, NULL)
})
observeEvent(input$select_all, {
  DT::selectRows(proxy, seq_len(nrow(filtered_data())))
})
```

### 8.2 reactable — Modern Tables

```r
library(reactable)

output$react_table <- renderReactable({
  reactable(
    filtered_data(),
    searchable = TRUE,
    striped = TRUE,
    highlight = TRUE,
    bordered = TRUE,
    defaultPageSize = 20,
    columns = list(
      name = colDef(name = "Name", minWidth = 150, sticky = "left"),
      value = colDef(
        name = "Value",
        cell = function(value) {
          width <- paste0(value / max(filtered_data()$value) * 100, "%")
          bar <- div(style = list(
            background = "#3fc1c9", width = width,
            height = "16px", borderRadius = "2px"
          ))
          div(style = list(display = "flex", alignItems = "center"),
            div(style = list(width = "50px"), value),
            bar
          )
        }
      ),
      change = colDef(
        name = "Change",
        cell = function(value) {
          color <- if (value >= 0) "#28a745" else "#dc3545"
          icon <- if (value >= 0) "\u25B2" else "\u25BC"
          div(style = list(color = color), paste(icon, abs(value), "%"))
        }
      )
    ),
    theme = reactableTheme(
      headerStyle = list(borderColor = "#555"),
      borderColor = "#ddd"
    )
  )
})
```

---

## 9. User Experience Enhancements

### 9.1 Notifications & Feedback

```r
# Instant notifications
showNotification("Saved successfully!", type = "message", duration = 3)
showNotification("Please check your input", type = "warning", duration = 5)
showNotification("Operation failed", type = "error", duration = NULL)  # Persistent

# Modal dialogs
showModal(modalDialog(
  title = "Confirm Deletion",
  "Are you sure you want to delete the selected records? This cannot be undone.",
  easyClose = FALSE,
  footer = tagList(
    modalButton("Cancel"),
    actionButton("confirm_delete", "Confirm Delete", class = "btn-danger")
  )
))

observeEvent(input$confirm_delete, {
  delete_records(state$selected_items)
  removeModal()
  showNotification("Deleted", type = "message")
})
```

### 9.2 Loading States

```r
# Method 1: shinycssloaders (simplest)
library(shinycssloaders)
withSpinner(plotOutput("plot"), type = 6, color = "#0054AD")

# Method 2: waiter (richer options)
library(waiter)
ui <- fluidPage(
  useWaiter(),
  actionButton("go", "Start Analysis"),
  plotOutput("result_plot")
)
server <- function(input, output, session) {
  w <- Waiter$new(
    id = "result_plot",
    html = spin_fading_circles(),
    color = "rgba(255,255,255,0.7)"
  )
  observeEvent(input$go, {
    w$show()
    Sys.sleep(3)
    output$result_plot <- renderPlot({ plot(iris) })
    w$hide()
  })
}

# Method 3: shinybusy (page-level)
library(shinybusy)
ui <- fluidPage(
  add_busy_spinner(spin = "fading-circle", position = "top-right")
)
```

### 9.3 shinyjs — Frontend Manipulation

```r
library(shinyjs)

ui <- fluidPage(
  useShinyjs(),  # Must enable in UI
  textInput("name", "Name"),
  actionButton("submit", "Submit"),
  div(id = "success_msg", style = "display:none;", "Submitted successfully!")
)

server <- function(input, output, session) {
  observe({
    # Enable/disable buttons
    toggleState("submit", condition = nchar(input$name) > 0)
  })

  observeEvent(input$submit, {
    # Show/hide elements
    show("success_msg")
    delay(3000, hide("success_msg"))  # Hide after 3 seconds

    # Add/remove CSS classes
    addClass("submit", "btn-success")
    delay(1000, removeClass("submit", "btn-success"))

    # Reset inputs
    reset("name")

    # Run arbitrary JavaScript
    runjs("console.log('submitted!');")
  })
}
```

### 9.4 Download Handlers

```r
# Download CSV
output$download_csv <- downloadHandler(
  filename = function() {
    paste0("data_export_", Sys.Date(), ".csv")
  },
  content = function(file) {
    readr::write_csv(filtered_data(), file)
  }
)

# Download plot (PNG)
output$download_plot <- downloadHandler(
  filename = function() { paste0("chart_", Sys.Date(), ".png") },
  content = function(file) {
    ggsave(file, plot = current_plot(), width = 10, height = 6, dpi = 300)
  }
)

# Download Excel (multi-sheet)
output$download_excel <- downloadHandler(
  filename = function() { paste0("report_", Sys.Date(), ".xlsx") },
  content = function(file) {
    wb <- openxlsx::createWorkbook()
    openxlsx::addWorksheet(wb, "Data")
    openxlsx::writeData(wb, "Data", filtered_data())
    openxlsx::addWorksheet(wb, "Summary")
    openxlsx::writeData(wb, "Summary", summary_data())
    openxlsx::saveWorkbook(wb, file)
  }
)
```

### 9.5 Bookmarking

```r
# Allow users to save and share application state
ui <- function(request) {
  fluidPage(
    bookmarkButton(),
    selectInput("species", "Species", choices = unique(iris$Species)),
    plotOutput("plot")
  )
}

server <- function(input, output, session) {
  output$plot <- renderPlot({ ... })

  # Exclude specific inputs from bookmarking
  setBookmarkExclude(c("password", "secret_token"))
}

shinyApp(ui, server, enableBookmarking = "url")  # Or "server"
```

---

## 10. Error Handling & Debugging

### 10.1 Wrapping Critical Operations with tryCatch

```r
server <- function(input, output, session) {

  loaded_data <- reactive({
    req(input$file)
    tryCatch({
      data <- readr::read_csv(input$file$datapath)
      # Data validation
      required_cols <- c("id", "date", "value")
      missing <- setdiff(required_cols, names(data))
      if (length(missing) > 0) {
        showNotification(
          paste("Missing required columns:", paste(missing, collapse = ", ")),
          type = "error"
        )
        return(NULL)
      }
      data
    }, error = function(e) {
      showNotification(paste("Read failed:", e$message), type = "error")
      NULL
    })
  })

  output$plot <- renderPlot({
    req(loaded_data())
    tryCatch({
      ggplot(loaded_data(), aes(x = date, y = value)) + geom_line()
    }, error = function(e) {
      plot.new()
      text(0.5, 0.5, paste("Plot error:", e$message), col = "red", cex = 1.2)
    })
  })
}
```

### 10.2 Debugging Tools

```r
# 1. browser(): set breakpoints inside reactives
filtered_data <- reactive({
  browser()  # Execution pauses here – inspect variables in R console
  iris |> filter(Species == input$species)
})

# 2. Console logging
observe({
  message("[DEBUG] input$species = ", input$species)
  message("[DEBUG] nrow(filtered_data) = ", nrow(filtered_data()))
})

# 3. reactlog: visualize the reactive dependency graph
# Set before launching:
options(shiny.reactlog = TRUE)
# While app is running, press Ctrl+F3 (Mac: Cmd+F3) to open the reactlog viewer

# 4. Verbose tracing
options(shiny.trace = TRUE)              # Detailed websocket messages
options(shiny.fullstacktrace = TRUE)     # Full stack traces on error
```

### 10.3 Common Error Quick Reference

| Error Message | Common Cause | Solution |
|---------------|-------------|----------|
| `object of type 'closure' is not subsettable` | Forgot `()` when calling a reactive | `data()` not `data` |
| `Operation not allowed without an active reactive context` | Read `input$` outside a reactive context | Wrap in `reactive()`, `observe()`, or `render*()` |
| `cannot coerce type 'closure' to vector` | Used a reactive as a plain value | Check for missing `()` |
| `could not find function "ns"` | Forgot to define `ns` in module UI | Add `ns <- NS(id)` |
| `Detected input/output ID collision` | Two components share the same ID | Ensure unique IDs or use modules |
| Plot not displaying | Used plotly inside `renderPlot` | `renderPlot` pairs with `plotOutput`; `renderPlotly` with `plotlyOutput` |
| Download returns empty file | `content` in `downloadHandler` didn't write to the `file` argument | Ensure you write to the `file` path |

---

## 11. Testing Strategy

### 11.1 shinytest2 — End-to-End Testing

```r
library(shinytest2)

test_that("Filter functionality works", {
  app <- AppDriver$new(app_dir = ".", name = "filter-test")

  # Set inputs
  app$set_inputs(species = "setosa")
  app$set_inputs(n = 25)
  app$click("apply")

  # Wait for output to update
  app$wait_for_idle()

  # Screenshot comparison
  app$expect_screenshot()

  # Check output values
  output_val <- app$get_value(output = "row_count")
  expect_equal(output_val, "25 rows")

  app$stop()
})
```

### 11.2 testServer — Server Logic Unit Testing

```r
library(testthat)

test_that("mod_data_filter correctly filters data", {
  testServer(mod_data_filter_server, args = list(data = reactive(iris)), {
    # Set inputs
    session$setInputs(variable = "Sepal.Length", range = c(5, 6))
    session$setInputs(apply = 1)  # Simulate click

    # Check the returned reactive
    result <- session$getReturned()
    expect_true(all(result()$Sepal.Length >= 5))
    expect_true(all(result()$Sepal.Length <= 6))
  })
})
```

### 11.3 Pure Function Unit Testing

```r
# Pure functions in fct_helpers.R can be tested directly with testthat
test_that("calculate_growth computes growth rate correctly", {
  expect_equal(calculate_growth(100, 120), 0.2)
  expect_equal(calculate_growth(100, 80), -0.2)
  expect_error(calculate_growth(0, 100))  # Division by zero handling
})
```

---

## 12. Deployment & Production

### 12.1 Deployment Options

| Platform | Best For | Key Features |
|----------|----------|-------------|
| **shinyapps.io** | Quick prototype sharing | Zero ops, free tier available |
| **Posit Connect** | Enterprise deployment | Access control, scheduled reports, API publishing |
| **ShinyProxy** | Self-hosted, multi-user | Docker container isolation, open source |
| **Docker + Nginx** | Full control | Flexible but requires DevOps capability |

### 12.2 Docker Deployment

```dockerfile
FROM rocker/shiny:4.3.0

# System dependencies
RUN apt-get update && apt-get install -y \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    && rm -rf /var/lib/apt/lists/*

# R packages
RUN R -e "install.packages(c('dplyr', 'ggplot2', 'DT', 'bslib', 'plotly', 'readr'), repos='https://cran.r-project.org')"

# Application code
COPY . /srv/shiny-server/myapp/

# Configuration
COPY shiny-server.conf /etc/shiny-server/shiny-server.conf

EXPOSE 3838

CMD ["/usr/bin/shiny-server"]
```

### 12.3 Production Configuration

```r
# app.R production settings

# Error handling: don't expose stack traces in production
options(shiny.sanitize.errors = TRUE)

# Logging configuration
if (Sys.getenv("SHINY_ENV") == "production") {
  options(shiny.trace = FALSE)
  # Custom error handler
  options(shiny.error = function() {
    log_error(geterrmessage())  # Write to log instead of displaying to user
  })
}

# Read environment variables
db_host <- Sys.getenv("DB_HOST", "localhost")
api_key <- Sys.getenv("API_KEY")
```

---

## 13. Security

### 13.1 Input Validation

```r
server <- function(input, output, session) {
  # Never trust user input
  safe_query <- reactive({
    req(input$search)
    # Prevent SQL injection: use parameterized queries
    dbGetQuery(con, "SELECT * FROM users WHERE name = ?", params = list(input$search))
  })

  # File upload security
  observeEvent(input$file, {
    req(input$file)
    # Validate file size
    if (input$file$size > 50 * 1024 * 1024) {  # 50MB
      showNotification("File too large", type = "error")
      return()
    }
    # Validate file type (don't rely solely on extension)
    mime <- mime::guess_type(input$file$datapath)
    allowed <- c("text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if (!(mime %in% allowed)) {
      showNotification("Unsupported file type", type = "error")
      return()
    }
  })
}
```

### 13.2 Configuration Options

```r
# Limit upload file size (in bytes)
options(shiny.maxRequestSize = 30 * 1024^2)  # 30MB

# Hide error details in production
options(shiny.sanitize.errors = TRUE)
```

---

## 14. Common Anti-Patterns & Pitfalls

### 14.1 Reactive Pitfalls

```r
# BAD: Modifying external state inside a reactive
values <- list()
reactive({
  values$data <- input$x  # Don't do this! Side effect in a reactive expression
})

# GOOD: Use observeEvent for side effects
state <- reactiveValues(data = NULL)
observeEvent(input$x, {
  state$data <- input$x
})

# BAD: Reactive that is never consumed
reactive({
  expensive_computation(input$x)  # If nothing reads this reactive, it never executes
})

# BAD: Nesting reactive expressions
filtered <- reactive({
  reactive({  # Nested reactive — this is a mistake
    iris |> filter(Species == input$species)
  })
})

# GOOD: Keep it flat
filtered <- reactive({
  iris |> filter(Species == input$species)
})

# BAD: observe reading unnecessary dependencies
observe({
  data <- filtered_data()      # Dependency 1
  threshold <- input$threshold  # Dependency 2
  if (nrow(data) > threshold) {
    showNotification("Data exceeds threshold")
  }
  # Problem: changing threshold also triggers, even if data hasn't changed
})

# GOOD: Use observeEvent for precise control
observeEvent(filtered_data(), {
  if (nrow(filtered_data()) > isolate(input$threshold)) {
    showNotification("Data exceeds threshold")
  }
})
```

### 14.2 Performance Pitfalls

```r
# BAD: Reading data redundantly in multiple render functions
output$plot1 <- renderPlot({ ggplot(read.csv("big.csv"), ...) })
output$plot2 <- renderPlot({ ggplot(read.csv("big.csv"), ...) })

# GOOD: Share a reactive data source
data <- reactive({ read.csv("big.csv") })
output$plot1 <- renderPlot({ ggplot(data(), ...) })
output$plot2 <- renderPlot({ ggplot(data(), ...) })

# BAD: renderUI rebuilding large UI blocks
output$filters <- renderUI({
  # Rebuilds all 10 dropdowns every time input$dataset changes
  lapply(1:10, function(i) selectInput(...))
})

# GOOD: Use updateXxxInput for incremental updates
observe({
  new_choices <- get_choices(input$dataset)
  lapply(1:10, function(i) {
    updateSelectInput(session, paste0("filter_", i), choices = new_choices)
  })
})
```

### 14.3 Module Pitfalls

```r
# BAD: Directly accessing parent-level input inside a module
mod_server <- function(id) {
  moduleServer(id, function(input, output, session) {
    data <- reactive({
      iris |> filter(Species == input$species)  # This is the MODULE's input, not the parent's
    })
  })
}

# GOOD: Pass data in via parameters
mod_server <- function(id, selected_species) {
  moduleServer(id, function(input, output, session) {
    data <- reactive({
      iris |> filter(Species == selected_species())
    })
  })
}
# Pass a reactive when calling
mod_server("my_mod", selected_species = reactive(input$species))

# BAD: Module returning a non-reactive value
mod_server <- function(id) {
  moduleServer(id, function(input, output, session) {
    result <- iris |> filter(...)  # Executes only once!
    return(result)                 # Returns a static value
  })
}

# GOOD: Return a reactive
mod_server <- function(id) {
  moduleServer(id, function(input, output, session) {
    result <- reactive({ iris |> filter(Species == input$species) })
    return(result)  # Returns a reactive expression
  })
}
```

### 14.4 R Vectorization Pitfalls (integrate, curves, apply-family)

**CRITICAL RULE: any function passed to `integrate()`, `curve()`, `outer()`, `optimize()`, `uniroot()`, or used to compute survival/hazard/density curves over a vector `t` MUST be vectorized — it must return a numeric vector of the SAME LENGTH as its input.** `integrate()` calls the function with a vector of quadrature points; if the function returns a scalar, R errors with `"evaluation of function gave a result of wrong length"`.

```r
# BAD: constant hazard that returns a scalar regardless of length(t)
h0_func <- function(t) input$h0_rate
integrate(h0_func, 0, 5)  # ERROR: evaluation of function gave a result of wrong length

# GOOD: replicate the constant to match the input length
h0_func <- function(t) rep(input$h0_rate, length(t))
integrate(h0_func, 0, 5)  # works

# BAD: if/else only inspects the first element of t — wrong values or warnings/errors
h1_func <- function(t) {
  if (t < input$t_switch) input$h1_rate1 else input$h1_rate2
}

# GOOD: ifelse() is vectorized element-wise
h1_func <- function(t) ifelse(t < input$t_switch, input$h1_rate1, input$h1_rate2)

# GOOD: arithmetic on t, pmin/pmax, and ifelse all preserve length
weibull_hazard <- function(t) (shape / scale) * (t / scale)^(shape - 1)
capped <- function(t) pmin(rate_max, base_rate * t)

# If a function genuinely cannot be vectorized (e.g., it itself calls integrate),
# wrap it before passing it on:
S_func <- function(t) exp(-integrate(h0_func, 0, t)$value)   # scalar-only
S_vec  <- Vectorize(S_func)                                   # safe for curve()/sapply()
# or: S_vec <- function(t) sapply(t, S_func)
```

Rules to apply when generating any numerical/statistical R code:
- A function body that returns a constant or otherwise ignores `t` must be wrapped in `rep(value, length(t))`.
- Use vectorized constructs (`ifelse()`, arithmetic on `t`, `pmin()`/`pmax()`, logical indexing) instead of `if`/`else`, which only evaluates the condition on the first element.
- Cumulative hazards from `integrate()` must be computed per time point (`sapply(t_grid, function(tt) integrate(h_func, 0, tt)$value)`) — never `integrate(h_func, 0, t_grid)` with a vector upper limit.
- `integrate()` returns a list; extract the number with `$value` before using it in arithmetic or plotting.

### 14.5 General R Correctness Pitfalls

```r
# BAD: 1:n breaks when n == 0 (produces c(1, 0) and iterates backwards)
for (i in 1:nrow(df)) { ... }
# GOOD:
for (i in seq_len(nrow(df))) { ... }

# BAD: single-column subsetting silently drops to a vector, breaking downstream code
sub <- df[, cols_selected]        # a vector if length(cols_selected) == 1
# GOOD:
sub <- df[, cols_selected, drop = FALSE]

# BAD: using inputs before they exist — renders run once before the user acts,
# and file/select inputs are NULL at startup
output$plot <- renderPlot({
  data <- read.csv(input$file$datapath)  # crashes: input$file is NULL initially
})
# GOOD: guard every render/reactive on the inputs it needs
output$plot <- renderPlot({
  req(input$file)
  data <- read.csv(input$file$datapath)
})

# BAD: assuming text input is numeric
threshold <- input$threshold_text * 2   # error if it came from textInput()
# GOOD: use numericInput()/sliderInput() for numbers; if text is unavoidable,
# convert and validate:
threshold <- as.numeric(input$threshold_text)
validate(need(!is.na(threshold), "Please enter a numeric threshold"))

# BAD: comparing floating point with ==
if (total == 1.0) { ... }
# GOOD:
if (isTRUE(all.equal(total, 1.0))) { ... }

# BAD: sample(x) surprise — when x is a single number n, it samples from 1:n
sample(ids)       # if ids happens to have length 1, this is sample(1:ids)
# GOOD:
ids[sample.int(length(ids))]

# BAD: apply() over a data frame coerces everything to a common type (often character)
apply(df, 1, function(row) row$age + 1)
# GOOD: use vectorized column operations or dplyr::rowwise()/mapply()

# BAD: is.na() check after == on possibly-NA values
if (df$status == "active") { ... }   # NA in status makes the condition NA -> error in if()
# GOOD:
if (isTRUE(df$status == "active")) { ... }   # or filter NAs out first
```

### 14.6 Custom / Non-CRAN Package APIs — Never Guess Signatures

**CRITICAL RULE: when calling functions from a custom, non-CRAN package (e.g. `nphDesign`, `nphRshiny`), do NOT guess function signatures, argument names, or expected object types from a prose description.** Guessed calls pass wrong argument names, wrong hazard/data formats, or feed the wrong object between functions, and fail at runtime inside the package (e.g. "evaluation of function gave a result of wrong length", or silent wrong output).

The real API comes from `formals()` and the package help-page examples:

```r
formals(nphDesign::explore.nphDesign)
formals(nphDesign::finalize.nphDesign)
formals(nphDesign::display.nphDesign)
?nphDesign::display.nphDesign   # Examples section shows the intended object flow
?nphDesign::finalize.nphDesign
```

Rules when the specification provides signatures, parameters, usage details, or reference code:

- **Use the exact argument names given.** Do not rename, add, or drop arguments. If an argument you would expect (like sample size or study duration) does not appear in the provided signature, do not invent it.
- **Respect the documented object flow.** If `display.nphDesign` expects an object created by `finalize.nphDesign(..., show.setting = "Y")`, generate that exact chain. Do not substitute a different constructor (like `explore.nphDesign`) unless the docs explicitly show its output is accepted downstream.
- **Match the expected argument TYPE, not just the name.** A hazard parameter may want a piecewise rate vector, cut points, a hazard-ratio spec, or an R function. Determine which from the example call and the `formals()` defaults, and supply that exact form. Do not assume hazards are function-valued closures.
- **Prefer replicating a working example call from the package's own help page** over constructing a call from scratch. Adapt the example's argument values to the Shiny inputs, but keep its structure, argument names, and object flow intact.
- **If real signatures are NOT available**, do not silently generate a call from the prose description. Emit the best-guess call preceded by a prominent comment block stating the call is UNVERIFIED and telling the user how to verify it:

```r
# WARNING: UNVERIFIED CALL — the signature of my_pkg::my_fn() was not provided.
# Verify before use by running:
#   formals(my_pkg::my_fn)
#   ?my_pkg::my_fn
# and correct the argument names/types below to match.
result <- my_pkg::my_fn(...)
```

- The vectorization rule (§14.4) still applies, but only where the package actually accepts function-valued arguments — the real signature confirms whether it does. If the signature shows a rate vector + cut points instead of a function, supply vectors, not closures.

### 14.7 Custom Package Dependency Chains — the Endpoint Is Not Enough

**CRITICAL RULE: a mapped/displayed function from a custom package is an ENDPOINT that usually depends on other functions from the same package. A display, plot, or summary function typically requires an object built by an upstream constructor (e.g. `display.nphDesign` requires an object from `finalize.nphDesign`). Those dependency functions are just as required as the mapped one, even when the spec only documents the endpoint.**

Apply this dependency rule before generating any call:

1. **Identify every dependency.** Read the mapped function's parameter descriptions and usage example and find every other package function it depends on. Signals: a parameter described as "an object generated by X()", "output of Y()", "result from Z()", a precondition like "must set arg = value when calling X()", or an example referencing a variable clearly produced by another call.

2. **Each dependency needs a real API too.** If the specification documents the dependency (exact argument names, types, usage example), use that verbatim. If it does not, DO NOT invent the dependency's signature. Surface the gap explicitly: state which function is undocumented and that the app cannot run end to end until its signature is supplied, because its output is required input for the mapped function. The user can supply it by running:

```r
formals(pkg::dependency_fn)
?pkg::dependency_fn   # and copy the Examples section
```

3. **If forced to proceed without it**, generate the dependency call as a clearly marked best guess:

```r
# WARNING: UNVERIFIED CALL — the signature of pkg::dependency_fn() was NOT provided.
# Its output is required input for pkg::endpoint_fn(), so the app cannot run
# end to end until this call is corrected. Verify by running:
#   formals(pkg::dependency_fn)
#   ?pkg::dependency_fn
design_obj <- pkg::dependency_fn(...)   # best guess — arguments unverified
```

Never mark a call verified when its arguments were guessed, and never let an unverified guess masquerade as working code.

4. **Preserve the documented object flow exactly.** If the endpoint requires the constructor to be called with a specific argument (like `show.setting = "Y"`), generate that argument ON the constructor call — not just a comment about it. The chain must be constructor → object → endpoint, matching whatever the docs specify:

```r
# GOOD: the required constructor argument is actually passed
design <- nphDesign::finalize.nphDesign(..., show.setting = "Y")
nphDesign::display.nphDesign(design)

# BAD: endpoint called on an object built the wrong way, requirement left as a comment
design <- nphDesign::explore.nphDesign(...)  # remember show.setting = "Y"!
nphDesign::display.nphDesign(design)
```

All rules from §14.4–14.6 remain in force alongside this one. **The general principle: a generated app is only complete when every function in the required call chain has a verified signature. Documenting the final endpoint is not enough if the object feeding it comes from an undocumented function — surface that gap explicitly rather than filling it with a guess.**

### 14.8 Consuming a Mapped Function's Output — Call It as a Black Box

**CRITICAL RULE: the Source / Reference Implementation of a mapped function is provided so you can understand its arguments, object flow, and preconditions — NOT so you can reimplement, split, or copy from it.** Never lift sections, loops, or plot calls out of a function's body into the app. Call the mapped function as a single black box and handle only its return value or side effects. If the body has multiple internal steps (several plots, several computations), those are internal to that one call — not separate outputs to expose as separate panels.

**The number of outputs in the app is determined by the number of times you CALL mapped functions, not by the number of plots or steps inside them.** One mapped function call = one output region, unless the function's documented return value is explicitly a collection meant to be shown separately.

Determine each function's output mode from its Source and Returns fields, and match the wrapper to it:

```r
# 1. Function draws base-R graphics as a SIDE EFFECT
#    (body calls plot()/lines()/abline()..., returns nothing or invisibly)
#    -> call it ONCE in ONE renderPlot on one device.
output$curves <- renderPlot({
  plot_km_curves(design)   # a single call; may draw several base plots internally
})
# If the body draws multiple base plots, lay them out on ONE device — do NOT
# make one plotOutput per internal plot:
output$curves <- renderPlot({
  op <- par(mfrow = c(2, 2))   # sized to the number of internal plots
  on.exit(par(op))             # restore par afterwards
  plot_km_curves(design)
}, height = 700)               # give the single output room for the grid

# 2. Function RETURNS a ggplot object -> print() the returned object, one output.
output$gg <- renderPlot({
  print(make_hazard_ggplot(design))
})

# 3. Function RETURNS a list of plots / a combined patchwork/grid object
#    -> render from that returned value's structure; don't re-derive the pieces.
output$panel <- renderPlot({
  combined <- make_all_plots(design)   # e.g. returns a patchwork object
  print(combined)
})

# 4. Output mode UNCLEAR (Returns is NOT PROVIDED and the body is truncated)
#    -> do NOT guess a decomposition. Call once into a single output and flag it.
output$result <- renderPlot({
  # NOTE: output mode of run_analysis() is UNVERIFIED — confirm whether it draws
  # directly, returns a plot object, or returns a list, then adjust this wrapper.
  run_analysis(design)
})
```

### 14.9 Boundary Correctness — Undocumented Helpers, Vector Lengths, Truncated Bodies

Because failures hide inside the black box of a called function (§14.8), the generated app must be correct AT THE BOUNDARY: faithful constructor calls, validated input lengths, and no reliance on truncated or undocumented internals.

**A. Undocumented internal helpers = an unverified object contract.** A mapped function's body may call a helper that is NOT documented in the spec, on its own input object (e.g. `nph <- f.extract(nphDesign)` at the top of `display.nphDesign`). The fields that helper reads are a hidden contract the constructor's output must satisfy but that is not written down anywhere. Do NOT reconstruct which fields the helper needs, and do NOT trim/reshape/"optimize" the constructor call to only the fields you think are used — replicate the documented constructor example exactly and assume its output is compatible. Flag the helper:

```r
# NOTE: display.nphDesign calls f.extract() internally; the object from
# finalize.nphDesign is assumed compatible. Verify with str() on the
# constructor output if this errors.
design <- nphDesign::finalize.nphDesign(<exactly as the documented example>)
nphDesign::display.nphDesign(design)
```

A technically-correct-looking but reshaped constructor call can still produce an object that fails deep inside the black box, with an error that gives no hint of the real cause. Constructor fidelity is the only defense.

**B. Validate lengths of related vector inputs before calling.** When the source shows arguments that must have matching or related lengths (the body indexes them together — `alpha[i]`, `T[j]` — or derives relationships like `K <- length(f.ws)` and `timing <- targetEvents / targetEvents[K]`), check them at the boundary and fail with a clear message instead of passing mismatched vectors in:

```r
# Parse comma-separated text inputs to numeric, then validate before the call
analysis_times <- as.numeric(strsplit(input$times_text, ",")[[1]])
alpha_spend    <- as.numeric(strsplit(input$alpha_text, ",")[[1]])
validate(
  need(!any(is.na(analysis_times)), "Analysis times must be comma-separated numbers."),
  need(!any(is.na(alpha_spend)),     "Alpha values must be comma-separated numbers."),
  need(length(analysis_times) == length(alpha_spend),
       "Provide one alpha value per analysis time (lengths must match).")
)
result <- pkg::some_design(T = analysis_times, alpha = alpha_spend)
```

A length mismatch among parallel vector arguments detonates inside the function as a "wrong length" or "length zero" error that is hard to trace to the input. Guarding at the boundary turns an opaque internal crash into a clear user-facing message.

**C. A truncated Source body counts as NOT PROVIDED for a directly-called function.** If a function the app calls directly has a Source that is cut off mid-function, treat it like NOT PROVIDED: mark the call `# WARNING: UNVERIFIED CALL`, name the function, and tell the user to run `formals(pkg::fn)`, `print(pkg::fn)`, and `?pkg::fn` and paste the FULL body back. A truncated body is only safe to rely on for a function that is an internal dependency the app never calls directly (see A).

---

## 15. Package Quick Reference

### 15.1 UI & Layout

| Package | Purpose | Key Functions |
|---------|---------|--------------|
| **bslib** | Modern Bootstrap 5 theming and layout | `page_sidebar()`, `card()`, `value_box()`, `layout_columns()` |
| **shinydashboard** | Admin-panel style layout | `dashboardPage()`, `box()`, `infoBox()` |
| **shinydashboardPlus** | shinydashboard extensions | `userBox()`, `socialBox()`, `timeline()` |
| **shinyWidgets** | Rich input controls | `pickerInput()`, `switchInput()`, `knobInput()`, `airDatepickerInput()` |
| **bsicons** | Bootstrap icons | `bs_icon("graph-up")` |

### 15.2 Visualization

| Package | Purpose | Output/Render Pair |
|---------|---------|-------------------|
| **ggplot2** | Static plots | `plotOutput` / `renderPlot` |
| **plotly** | Interactive charts | `plotlyOutput` / `renderPlotly` |
| **echarts4r** | Dynamic charts | `echarts4rOutput` / `renderEcharts4r` |
| **leaflet** | Maps | `leafletOutput` / `renderLeaflet` |
| **DT** | Interactive tables | `dataTableOutput` / `renderDataTable` |
| **reactable** | Modern tables | `reactableOutput` / `renderReactable` |
| **visNetwork** | Network graphs | `visNetworkOutput` / `renderVisNetwork` |
| **dygraphs** | Time series | `dygraphOutput` / `renderDygraph` |

### 15.3 Data Processing

| Package | Purpose |
|---------|---------|
| **dplyr** | Data manipulation (filter, mutate, summarise, join) |
| **tidyr** | Data reshaping (pivot_longer, pivot_wider, separate, unnest) |
| **readr** | Fast CSV/TSV reading |
| **readxl** | Read Excel files |
| **haven** | Read SAS/SPSS/Stata files |
| **lubridate** | Date/time handling |
| **stringr** | String manipulation |
| **forcats** | Factor manipulation |
| **janitor** | Data cleaning (clean_names, tabyl) |
| **glue** | String interpolation |

### 15.4 Infrastructure

| Package | Purpose |
|---------|---------|
| **shinyjs** | JavaScript operations (show/hide/toggle/enable/disable) |
| **htmltools** | HTML construction |
| **waiter** | Loading animations |
| **shinycssloaders** | Output loading spinners |
| **shinyFeedback** | Real-time input validation feedback |
| **shinyalert** | Popup dialogs |
| **pool** | Database connection pooling |
| **config** | Environment configuration management |
| **golem** | Production-grade app framework |
| **rhino** | Enterprise-grade app framework |
| **shinytest2** | End-to-end testing |
| **profvis** | Performance profiling |

### 15.5 nphRshiny (Non-Proportional Hazards Analysis)

The `nphRshiny` package is used for weighted log-rank tests and average hazard ratio (AHR) design/analysis under non-proportional hazards (NPH).

**Key Functions & Conventions:**
- `wlr(time, event, group, rho, gamma, tau)`: Performs a weighted log-rank test on data vectors.
  - `time`: numeric vector of survival times.
  - `event`: binary event vector (1 = event, 0 = censored).
  - `group`: binary treatment group vector (0 = control, 1 = experimental).
  - `rho`, `gamma`: Fleming-Harrington parameters.
  - `tau`: truncation/stabilization time.
  - Returns a list with `$test.results` (containing columns `z`, `chisq`, `p`, `test.side`).
- `plot_AHR(n, Tmax, r, h0, S0, h1, S1, rho, gamma, tau, ...)`: Design-based function that calculates expected average hazard ratio over time.
  - **Important:** Does NOT take a patient-level dataset. It accepts parameters like sample size `n`, time window `Tmax`, randomization ratio `r`, control hazard `h0(t)`, control survival `S0(t)`, experimental hazard `h1(t)`, experimental survival `S1(t)`.
  - Returns a numeric vector of AHRs of length `Tmax` which can be plotted. To plot from data, estimate `lambda` for both arms and feed the parametric functions to `plot_AHR`, then extract the returned vector to plot using `ggplot2`/`plotly`.
- `plot_S(S, Tmax, ...)`: Plots design-based survival curves for a list of survival functions `S = list(S0, S1)`. Does not accept patient-level data.

---

## 16. Code Template Library

### 16.1 Minimal Complete App Template

```r
library(shiny)
library(bslib)
library(dplyr)
library(ggplot2)

ui <- page_sidebar(
  title = "App Title",
  theme = bs_theme(version = 5, bootswatch = "flatly"),
  sidebar = sidebar(
    title = "Controls",
    fileInput("file", "Upload Data", accept = c(".csv", ".xlsx")),
    uiOutput("dynamic_controls"),
    actionButton("run", "Run Analysis", class = "btn-primary w-100")
  ),
  navset_card_tab(
    nav_panel("Visualization", plotly::plotlyOutput("main_plot", height = "500px")),
    nav_panel("Data", DT::dataTableOutput("data_table")),
    nav_panel("Summary", verbatimTextOutput("summary"))
  )
)

server <- function(input, output, session) {

  # Data loading
  raw_data <- reactive({
    req(input$file)
    ext <- tools::file_ext(input$file$name)
    tryCatch(
      switch(ext,
        csv = readr::read_csv(input$file$datapath, show_col_types = FALSE),
        xlsx = readxl::read_excel(input$file$datapath),
        { showNotification("Unsupported format", type = "error"); NULL }
      ),
      error = function(e) {
        showNotification(paste("Read failed:", e$message), type = "error")
        NULL
      }
    )
  })

  # Dynamic UI
  output$dynamic_controls <- renderUI({
    req(raw_data())
    cols <- names(raw_data())
    num_cols <- names(dplyr::select(raw_data(), where(is.numeric)))
    tagList(
      selectInput("x_var", "X Axis", choices = cols),
      selectInput("y_var", "Y Axis", choices = num_cols),
      selectInput("color_var", "Color Group", choices = c("None" = "", cols))
    )
  })

  # Analysis (event-driven)
  analysis_data <- eventReactive(input$run, {
    req(raw_data(), input$x_var, input$y_var)
    raw_data()
  })

  # Outputs
  output$main_plot <- plotly::renderPlotly({
    req(analysis_data(), input$x_var, input$y_var)
    p <- ggplot(analysis_data(), aes(
      x = .data[[input$x_var]],
      y = .data[[input$y_var]]
    ))
    if (isTruthy(input$color_var)) {
      p <- p + geom_point(aes(color = .data[[input$color_var]]), alpha = 0.7)
    } else {
      p <- p + geom_point(alpha = 0.7, color = "steelblue")
    }
    p <- p + theme_minimal(base_size = 14) + labs(x = input$x_var, y = input$y_var)
    plotly::ggplotly(p)
  })

  output$data_table <- DT::renderDataTable({
    req(analysis_data())
    DT::datatable(analysis_data(), options = list(pageLength = 20, scrollX = TRUE))
  })

  output$summary <- renderPrint({
    req(analysis_data())
    summary(analysis_data())
  })
}

shinyApp(ui, server)
```

### 16.2 Modular App Template

```r
# R/mod_data_upload.R
mod_data_upload_ui <- function(id) {
  ns <- NS(id)
  tagList(
    fileInput(ns("file"), "Choose File", accept = c(".csv", ".xlsx")),
    textOutput(ns("file_info"))
  )
}

mod_data_upload_server <- function(id) {
  moduleServer(id, function(input, output, session) {
    data <- reactive({
      req(input$file)
      ext <- tools::file_ext(input$file$name)
      switch(ext,
        csv = readr::read_csv(input$file$datapath, show_col_types = FALSE),
        xlsx = readxl::read_excel(input$file$datapath)
      )
    })

    output$file_info <- renderText({
      req(data())
      paste(nrow(data()), "rows x", ncol(data()), "columns")
    })

    return(data)
  })
}

# R/mod_visualization.R
mod_visualization_ui <- function(id) {
  ns <- NS(id)
  tagList(
    layout_columns(
      col_widths = c(3, 9),
      card(
        selectInput(ns("x"), "X Axis", choices = NULL),
        selectInput(ns("y"), "Y Axis", choices = NULL),
        selectInput(ns("geom"), "Chart Type",
          choices = c("Scatter" = "point", "Line" = "line",
                      "Bar" = "bar", "Boxplot" = "boxplot"))
      ),
      card(
        full_screen = TRUE,
        card_header("Chart"),
        plotly::plotlyOutput(ns("plot"), height = "100%")
      )
    )
  )
}

mod_visualization_server <- function(id, data) {
  moduleServer(id, function(input, output, session) {
    observe({
      req(data())
      cols <- names(data())
      num_cols <- names(dplyr::select(data(), where(is.numeric)))
      updateSelectInput(session, "x", choices = cols)
      updateSelectInput(session, "y", choices = num_cols)
    })

    output$plot <- plotly::renderPlotly({
      req(data(), input$x, input$y, input$geom)
      p <- ggplot(data(), aes(x = .data[[input$x]], y = .data[[input$y]]))
      p <- switch(input$geom,
        point = p + geom_point(alpha = 0.6),
        line = p + geom_line(),
        bar = p + geom_col(),
        boxplot = p + geom_boxplot()
      )
      p <- p + theme_minimal(base_size = 13)
      plotly::ggplotly(p)
    })
  })
}

# app.R
library(shiny)
library(bslib)
library(dplyr)
library(ggplot2)

# Load all modules
source("R/mod_data_upload.R")
source("R/mod_visualization.R")

ui <- page_navbar(
  title = "Modular App",
  theme = bs_theme(version = 5, bootswatch = "cosmo"),
  nav_panel("Data",
    layout_columns(
      col_widths = c(4, 8),
      card(card_header("Upload"), mod_data_upload_ui("upload")),
      card(card_header("Preview"), DT::dataTableOutput("preview"))
    )
  ),
  nav_panel("Visualization",
    mod_visualization_ui("viz")
  )
)

server <- function(input, output, session) {
  uploaded_data <- mod_data_upload_server("upload")
  mod_visualization_server("viz", data = uploaded_data)

  output$preview <- DT::renderDataTable({
    req(uploaded_data())
    DT::datatable(head(uploaded_data(), 100))
  })
}

shinyApp(ui, server)
```

### 16.3 Database Connection Template

```r
# global.R
library(pool)
library(DBI)

pool <- dbPool(
  drv = RPostgres::Postgres(),
  dbname = Sys.getenv("DB_NAME", "mydb"),
  host = Sys.getenv("DB_HOST", "localhost"),
  port = as.integer(Sys.getenv("DB_PORT", "5432")),
  user = Sys.getenv("DB_USER"),
  password = Sys.getenv("DB_PASS"),
  minSize = 2,
  maxSize = 10
)

onStop(function() {
  poolClose(pool)
})

# server.R
# Example usage of the database pool in a server function:
server <- function(input, output, session) {
  # Querying data dynamically from the pool
  query_data <- reactive({
    req(input$filter_value)
    
    # Secure parameterized query via DBI
    dbGetQuery(pool, "SELECT * FROM sales_data WHERE category = $1", 
               params = list(input$filter_value))
  })
  
  # Rendering the queried database values
  output$db_table <- DT::renderDataTable({
    req(query_data())
    DT::datatable(query_data())
  })
}
```
