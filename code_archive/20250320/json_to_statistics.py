import time
start_time = time.time()

import json
import pandas as pd
json_path = 'D:\\DEVELOP\\projects\\backup_enterprise\\info_data.json'
dic = json.load(open(json_path))
df = pd.DataFrame(dic)
print("Number of unique checksums:", df['checksum'].nunique())


print("Most common extensions:")
print(df['extention'].value_counts().head())

cumulative_size_per_extension = df.groupby('extention')['size'].sum()
print("Cumulative size per extension:")
print("Largest 5 cumulative sizes per extension:")
print(cumulative_size_per_extension.sort_values(ascending=False).head(25))
print("Smallest 5 cumulative sizes per extension:")
print(cumulative_size_per_extension.sort_values(ascending=True).head(5))


checksum_counts = df.groupby('checksum').size()
print("Largest classes by checksum count:")
print(checksum_counts.sort_values(ascending=False).head(10))



end_time = time.time()
print("Time taken for script to run:", end_time - start_time, "seconds")