# Multi-store Display Resource Efficiency & Allocation Optimization

A portfolio-ready retail decision system built on the CC0 84.51° Complete Journey data. It turns anonymous transactions, products, and promotion/display records into a DuckDB analytics model, leakage-aware baseline estimates, OR-Tools CP-SAT allocation recommendations, and a recommendation-to-audit loop.

## Data truth contract

- **Real anonymous:** Complete Journey transactions, products, promotions, and display codes.
- **Model estimated:** expected sales without special display, predicted incremental sales, and support-based confidence.
- **Simulated business configuration:** capacity, position IDs, current allocation, fit rules, change costs, strategic policies, and field audits. Every such row is labelled `data_source=simulated`.

Observed display performance is not causal. Allocation was not randomized and unobserved inventory, traffic, pricing, selection, and execution can confound estimates. All benefits are labelled model predictions or scenario simulations.

## Run

```bash
make setup
make demo
make build
make report
make test
make dashboard
```

The repository already includes a small converted official demo, so `make demo` is only required when refreshing it. Open `outputs/portfolio_report.html` for an offline report.

See [architecture](docs/architecture.md), [data dictionary](docs/data_dictionary.md), [methodology](docs/methodology.md), and the [Chinese README](README.md).

