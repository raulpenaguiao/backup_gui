import json
import pandas as pd
import os
from collections import Counter
import matplotlib.pyplot as plt


def save_dic_to_json(dic, path):
    try:
        with open(path, 'w') as f:
            json.dump(dic, f, indent=4)
    except Exception as e:
        print(f"An error occurred: {e}")




if __name__ == "__main__":
    folder_path = input()
    if folder_path[0] == '"':
        folder_path = folder_path[1:-1]
    
    drive_path = os.path.join(folder_path, '.driveinfo')
    json_path = os.path.join(drive_path,  '.fileinfo.json')
    checksumjson_path = os.path.join(drive_path,  '.checksuminfo.json')
    dic = json.load(open(json_path))
    dic_checksum = json.load(open(checksumjson_path))
    df = pd.DataFrame(dic)

    #Statistics about extentions
    cumulative_size_per_extension = df.groupby('extention')['size'].sum()
    cumulative_size_per_extension = cumulative_size_per_extension.sort_values(ascending=False)
    cumulative_size_per_extension.plot(kind='bar')
    plt.xlabel('File Extension')
    plt.ylabel('Cumulative Size')
    plt.yscale('log')
    plt.title('Cumulative Size per File Extension')
    print(f"Number of extensions: {len(cumulative_size_per_extension)}")
    plt.savefig(os.path.join(drive_path, 'cumulative_size_per_extension.png'))

    #Statistics about copies

    number_of_copies_per_file = []
    for checksum in dic_checksum:
        for file_list in dic_checksum[checksum]:
            number_of_copies_per_file.append(len(file_list["locations"]))
    
    print(f"Number of unique files: {len(number_of_copies_per_file)}")
    print(f"Number of total files: {sum(number_of_copies_per_file)}")
    # Count the number of each different value in the list number_of_copies_per_file
    counter = Counter(number_of_copies_per_file)
    # Convert the counter to a DataFrame for plotting
    counter_df = pd.DataFrame.from_dict(counter, orient='index').reset_index()
    counter_df.columns = ['Number of Copies', 'Number of Files']

    # Plot the counter as a bar graph
    counter_df = counter_df.sort_values(by='Number of Copies')
    counter_df.plot(kind='bar', x='Number of Copies', y='Number of Files', logy=True)
    plt.xlabel('Number of Copies')
    plt.ylabel('Number of Files with that Number of Copies')
    plt.yscale('log')
    plt.xticks(rotation=90, fontsize=4)
    plt.title('Number of Files per Number of Copies')
    plt.savefig(os.path.join(drive_path, 'number_of_files_per_number_of_copies.png'))


