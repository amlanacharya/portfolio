# VyaparBazaar Analytics Internship Camp Instructor Guide

This guide provides instructions and resources for leading the VyaparBazaar Analytics Internship Camp.

## Camp Overview

The internship camp is designed to teach data modeling and analytics engineering using dbt and DuckDB. The camp is structured around five modules, each building on the previous one.

### Learning Objectives

By the end of the camp, interns should be able to:

1. Understand the fundamentals of data modeling with dbt
2. Write SQL transformations using dbt best practices
3. Create and document data models for analytics
4. Test and validate data quality
5. Apply analytics engineering principles to real-world problems

## Module Breakdown

### Module 1: Introduction to dbt and Data Modeling (Day 1)

**Morning Session (3 hours)**
- Introduction to analytics engineering (45 min)
- dbt architecture and concepts (45 min)
- Project structure and organization (45 min)
- Setting up the development environment (45 min)

**Afternoon Session (3 hours)**
- Hands-on: Project exploration (Exercise 1.1)
- Hands-on: Understanding model dependencies (Exercise 1.2)
- Q&A and discussion

**Key Concepts to Emphasize:**
- The role of analytics engineering in the data stack
- The importance of modular, reusable SQL
- How dbt organizes and manages transformations

### Module 2: Data Transformation Fundamentals (Day 2)

**Morning Session (3 hours)**
- SQL basics in dbt (45 min)
- Jinja templating and macros (45 min)
- Sources and references (45 min)
- Testing basics (45 min)

**Afternoon Session (3 hours)**
- Hands-on: Create a new staging model (Exercise 2.1)
- Hands-on: Source configuration (Exercise 2.2)
- Code review and feedback

**Key Concepts to Emphasize:**
- Clean, readable SQL
- Proper use of Jinja for DRY code
- The importance of testing from the beginning

### Module 3: Advanced Data Modeling (Day 3)

**Morning Session (3 hours)**
- CTEs and modular SQL (45 min)
- Intermediate models and aggregations (45 min)
- Dimensional modeling concepts (45 min)
- Performance considerations (45 min)

**Afternoon Session (3 hours)**
- Hands-on: Enhance customer behavior model (Exercise 3.1)
- Hands-on: Create a new intermediate model (Exercise 3.2)
- Group discussion on modeling approaches

**Key Concepts to Emphasize:**
- Building models in layers
- Balancing readability and performance
- Thinking about the business context

### Module 4: Testing and Documentation (Day 4)

**Morning Session (3 hours)**
- Advanced testing strategies (45 min)
- Documentation best practices (45 min)
- Using dbt docs effectively (45 min)
- Version control with dbt (45 min)

**Afternoon Session (3 hours)**
- Hands-on: Add tests to models (Exercise 4.1)
- Hands-on: Enhance documentation (Exercise 4.2)
- Peer review of tests and documentation

**Key Concepts to Emphasize:**
- Tests as living documentation
- Writing for future analysts
- The importance of data quality

### Module 5: Analytics Engineering Best Practices (Day 5)

**Morning Session (3 hours)**
- Optimization techniques (45 min)
- Materialization strategies (45 min)
- Deployment and scheduling (45 min)
- Working with stakeholders (45 min)

**Afternoon Session (3 hours)**
- Hands-on: Optimize a complex model (Exercise 5.1)
- Hands-on: Create a mart model (Exercise 5.2)
- Final project kickoff

**Key Concepts to Emphasize:**
- Balancing technical excellence with business needs
- The importance of iteration
- Collaboration in analytics engineering

### Final Project (Day 6-7)

**Two Full Days**
- Interns work on the customer segmentation model
- Instructors provide guidance and feedback
- Final presentations and code reviews

## Teaching Tips

### Facilitating Hands-on Exercises

1. **Pair Programming:** Consider having interns work in pairs for exercises
2. **Check-ins:** Schedule regular check-ins during exercises
3. **Code Reviews:** Conduct brief code reviews after each exercise
4. **Troubleshooting:** Prepare for common issues (see below)

### Common Issues and Solutions

1. **DuckDB Connection Issues**
   - Verify path in profiles.yml
   - Check file permissions

2. **dbt Compilation Errors**
   - Check for syntax errors in SQL
   - Verify model references exist
   - Check for circular dependencies

3. **Port Issues with dbt docs serve**
   - Try different ports (8081, 8082, etc.)
   - Check for processes using the default port

4. **Performance Issues**
   - Look for inefficient joins
   - Check for unnecessary CTEs
   - Consider materialization strategies

### Assessment Criteria

Evaluate interns based on:

1. **Technical Skills**
   - SQL proficiency
   - dbt knowledge
   - Problem-solving ability

2. **Modeling Approach**
   - Clarity and organization
   - Performance considerations
   - Business alignment

3. **Documentation and Testing**
   - Test coverage
   - Documentation quality
   - Attention to detail

4. **Collaboration**
   - Communication
   - Code reviews
   - Teamwork

## Resources

### Required Reading for Instructors

- [dbt Best Practices](https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview)
- [Analytics Engineering Cookbook](https://www.getdbt.com/analytics-engineering/cookbook/)
- [Dimensional Modeling Techniques](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/)

### Additional Resources for Interns

- [dbt Learn](https://courses.getdbt.com/collections)
- [Modern Data Stack Blog](https://www.moderndatastack.xyz/)
- [DuckDB Documentation](https://duckdb.org/docs/)

## Feedback and Iteration

Collect feedback from interns daily to improve the camp experience. Consider using:

1. Daily retrospectives
2. Anonymous feedback forms
3. One-on-one check-ins

Use this feedback to adjust the pace and content of the camp as needed.
