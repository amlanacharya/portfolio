# VyaparBazaar Analytics Internship Camp

Welcome to the VyaparBazaar Analytics Internship Camp! This program is designed to provide hands-on experience with modern data modeling and analytics engineering using dbt and DuckDB.

## Camp Overview

This internship camp is structured around five learning modules, each building on the previous one, culminating in a final project. The camp combines theoretical knowledge with practical exercises to provide a comprehensive learning experience.

### Duration

The camp is designed to run for 7 days:
- Days 1-5: Learning modules (one module per day)
- Days 6-7: Final project work and presentations

### Learning Modules

1. **Introduction to dbt and Data Modeling**
   - dbt architecture and concepts
   - Project structure and organization
   - Setting up the development environment

2. **Data Transformation Fundamentals**
   - SQL basics in dbt
   - Jinja templating and macros
   - Sources and references
   - Testing basics

3. **Advanced Data Modeling**
   - CTEs and modular SQL
   - Intermediate models and aggregations
   - Dimensional modeling concepts
   - Performance considerations

4. **Testing and Documentation**
   - Advanced testing strategies
   - Documentation best practices
   - Using dbt docs effectively
   - Version control with dbt

5. **Analytics Engineering Best Practices**
   - Optimization techniques
   - Materialization strategies
   - Deployment and scheduling
   - Working with stakeholders

### Final Project

The final project involves creating a customer segmentation model that combines various data points to create features for machine learning. This project will allow interns to apply all the concepts learned throughout the camp.

## Getting Started

### For Interns

1. Read the [Intern Setup Guide](intern_setup_guide.md) to set up your development environment
2. Review the [Internship Exercises](internship_exercises.md) to understand what you'll be working on
3. Explore the project documentation by running `dbt docs serve --port 8081`

### For Instructors

1. Review the [Instructor Guide](instructor_guide.md) for detailed information on leading the camp
2. Familiarize yourself with the exercise solutions in the `exercise_solutions` directory
3. Prepare the environment for interns by ensuring all dependencies are available

## Project Structure

```
dbt_project/
├── models/                  # SQL models organized by layer
│   ├── staging/             # Basic cleaned versions of source tables
│   ├── intermediate/        # Transformed and joined models
│   ├── marts/               # Business-specific models
│   └── ml_features/         # ML-ready feature models
├── macros/                  # Reusable SQL snippets
├── tests/                   # Data quality tests
├── seeds/                   # Static data files
├── exercise_solutions/      # Solutions to internship exercises
├── dbt_project.yml          # Project configuration
├── profiles.yml             # Connection profiles
├── intern_setup_guide.md    # Setup guide for interns
├── instructor_guide.md      # Guide for instructors
└── internship_exercises.md  # Hands-on exercises for interns
```

## Learning Resources

### dbt Resources

- [dbt Documentation](https://docs.getdbt.com/)
- [dbt Learn](https://courses.getdbt.com/collections)
- [dbt Discourse](https://discourse.getdbt.com/)

### DuckDB Resources

- [DuckDB Documentation](https://duckdb.org/docs/)
- [DuckDB SQL Reference](https://duckdb.org/docs/sql/introduction)

### Analytics Engineering Resources

- [Analytics Engineering Cookbook](https://www.getdbt.com/analytics-engineering/cookbook/)
- [Modern Data Stack Blog](https://www.moderndatastack.xyz/)
- [Locally Optimistic](https://locallyoptimistic.com/)

## Contact Information

For questions or assistance, please contact the camp organizers:

- Email: [camp-organizers@vyaparbazaar.com](mailto:camp-organizers@vyaparbazaar.com)
- Slack: #analytics-internship-camp

## Acknowledgements

This internship camp is based on the VyaparBazaar Analytics Platform, which uses a transformed version of the [Brazilian E-commerce Public Dataset by OLIST](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).
