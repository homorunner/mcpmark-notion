# 📊 Task: Find Top 5 Departments by Average Salary

## 🧾 Description

You are given access to an employees database consisting of multiple tables related to departments, employees, their salaries, and organizational structure.

Your task is to:

Determine the top 5 departments with the highest average salary.

Only include salaries and department assignments that are currently active (i.e., their end dates are in the future).

Calculate the average salary per department based on current employee-salary associations.

Sort the results in descending order of average salary.

Write the final output (containing department name and average salary) into a new table named **results**.

You must derive the correct SQL query on your own using the schema and relationships between the tables.

## 📥 Output Requirement

Create a table named **results** with the following columns:

dept_name (string): the name of the department

average_salary (numeric): the calculated average salary for that department

Only include the top 5 departments.