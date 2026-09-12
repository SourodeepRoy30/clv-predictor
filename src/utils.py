def report_reduction(before_shape, after_shape, step_name="This step"):
    """
    Prints the number and percentage of rows removed by a filtering/cleaning step.

    Parameters:
        before_shape (tuple): DataFrame.shape before the filtering step
        after_shape (tuple): DataFrame.shape after the filtering step
        step_name (str): Description of the step, used in the printed output
    """
    rows_before = before_shape[0]
    rows_after = after_shape[0]
    rows_removed = rows_before - rows_after
    pct_removed = round((rows_removed / rows_before) * 100, 2)
    print(f"{step_name}:")
    print(f"  Before: {rows_before:,} rows")
    print(f"  After:  {rows_after:,} rows")
    print(f"  Removed: {rows_removed:,} rows ({pct_removed}%)")
