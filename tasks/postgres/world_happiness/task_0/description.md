# 📊 Task: Identify Happy but Low-GDP Countries

## 🧾 Description

You are working with the world_happiness database, specifically analyzing data from the 2019 table. This table includes various indicators such as happiness score, GDP per capita, and other well-being metrics for each country or region.

Your task is to:

- Find all countries or regions where the happiness score is above the global average, but the GDP per capita is below the global average.

- Focus only on the fields relevant to this analysis:

    - country_or_region

    - score

    - gdp_per_capita

- Sort the results by happiness score in descending order.

- Store the final output into a new table named **results**.

## 📥 Output Requirement

Create a table named **results** with the following columns:

- country_or_region (string): Name of the country or region

- score (numeric): The happiness score

- gdp_per_capita (numeric): GDP per capita

Only include entries that satisfy:

- score is greater than the average of all scores

- gdp_per_capita is less than the average of all GDP per capita values
