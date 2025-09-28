# gpu_monte_carlo.py (Corrected)
import random
from pyspark.sql import SparkSession
# Import the 'rand' function
from pyspark.sql.functions import col, udf, rand
from pyspark.sql.types import IntegerType

def main():
    spark = SparkSession.builder.appName("GpuMonteCarloPi").getOrCreate()
    num_samples = 100_000_000
    output_path = "s3a://lakehouse/pi_estimation_results"
    print(f"Starting Monte Carlo Pi estimation with {num_samples:,} samples.")
    print(f"Output will be written to: {output_path}")
    df = spark.range(num_samples).repartition(200)

    # Use the rand() function to generate random numbers as a Column expression
    points_df = df.withColumn("x", (rand() * 2 - 1)) \
                  .withColumn("y", (rand() * 2 - 1))

    in_circle_df = points_df.withColumn("in_circle", 
        (col("x") * col("x") + col("y") * col("y") <= 1).cast(IntegerType())
    )
    print("Performing aggregation...")
    count = in_circle_df.selectExpr("sum(in_circle)").first()[0]
    pi_estimate = 4.0 * count / num_samples
    print("-----------------------------------------")
    print(f"Points in circle: {count:,}")
    print(f"Total points:     {num_samples:,}")
    print(f"Pi is roughly:    {pi_estimate}")
    print("-----------------------------------------")
    print(f"Writing results to {output_path}...")
    result_df = spark.createDataFrame([(num_samples, count, pi_estimate)], ["total_samples", "points_in_circle", "pi_estimate"])
    result_df.write.mode("overwrite").parquet(output_path)
    print("Job completed successfully.")
    spark.stop()

if __name__ == "__main__":
    main()
