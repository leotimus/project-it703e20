import numpy as np
import pandas as pd
import math
import topKMetrics as topk

CHUNK_SIZE = 1E4
NUMBER_OF_CHUNKS_TO_EAT = 10
EPOCHS = 5
USER_ID_COLUMN = "user_id"
ITEM_ID_COLUMN = "item_id"
RATING_COLUMN = "rating"
LEARNING_RATE = 0.02
REGULARIZATION = 0.01

NUMBER_OF_FACTORS = 5

TRAIN_FILE_PATH = r"data/ml-100k/all.csv"
TEST_FILE_PATH = r"data/ml-100k/all.csv"
VERBOSE = False
PRINT_EVERY = 5000

def print_verbose(message):
    if VERBOSE:
        print(message)

def digest(data_chunks):
    user_ids = {}
    item_ids = {}
    next_user_id = 0
    next_item_id = 0

    total_so_far = 0
    average_so_far = 0

    number_of_chunks_to_eat = NUMBER_OF_CHUNKS_TO_EAT

    for chunk in data_chunks:
        next_user_id, next_item_id = convert_ids(chunk, user_ids, item_ids, next_user_id, next_item_id)

        chunk_total = chunk.shape[0]
        chunk_accumulator = 0

        total_so_far, average_so_far = calculate_average(chunk, total_so_far, average_so_far)
        
        number_of_chunks_to_eat -= 1
        if number_of_chunks_to_eat <= 0:
            break

    return user_ids, item_ids, next_user_id-1, next_item_id-1, average_so_far

def convert_ids(chunk, user_ids, item_ids, next_user_id, next_item_id):
    for index, row in chunk.iterrows():
        if not (row[USER_ID_COLUMN] in user_ids):
            user_ids[row[USER_ID_COLUMN]] = next_user_id
            next_user_id += 1
        
        if not (row[ITEM_ID_COLUMN] in item_ids):
            item_ids[row[ITEM_ID_COLUMN]] = next_item_id
            next_item_id += 1

        if index%PRINT_EVERY == 0:
            print_verbose("digesting... at index: {} next_item_id is {}".format(index, next_item_id))
        
    return next_user_id, next_item_id

def calculate_average(chunk, total_so_far, average_so_far):
    chunk_total = chunk.shape[0]
    chunk_accumulator = 0

    for index, row in chunk.iterrows():
        
        rating = row[RATING_COLUMN]

        chunk_accumulator += rating

        if index%PRINT_EVERY == 0:
            print_verbose(f"calculating global average... at index: {index} average so far is {average_so_far}")
    
    chunk_average = chunk_accumulator / chunk_total

    total_so_far += chunk_total
    average_so_far = ((chunk_total/total_so_far) * chunk_average) + (((total_so_far-chunk_total)/total_so_far) *average_so_far)

    return total_so_far, average_so_far

class svd_prediction_doer:
    def __init__(self, user_ids, item_ids, user_matrix, item_matrix, user_bias_vector, item_bias_vector, global_bias):
        self.user_matrix = user_matrix
        self.item_matrix = item_matrix
        self.user_bias_vector = user_bias_vector
        self.item_bias_vector = item_bias_vector
        self.global_bias = global_bias
        self.user_ids = user_ids
        self.item_ids = item_ids

    def predict(self, weird_array):
        user = self.user_ids[weird_array[0][0]]
        item = self.item_ids[weird_array[1][0]]
        return predict(user, item, self.user_matrix, self.item_matrix, self.user_bias_vector, self.item_bias_vector, self.global_bias)
         
def predict(user, item, user_matrix, item_matrix, user_bias_vector, item_bias_vector, global_bias):
    item_vector = item_matrix[item, :]
    user_vector = user_matrix[user, :]
    item_bias = item_bias_vector[item]
    user_bias = user_bias_vector[user]

    return user_bias + item_bias + global_bias + np.dot(item_vector, user_vector)

def  fit_model(data_chunks, user_matrix, item_matrix, user_bias_vector, item_bias_vector, global_bias, user_ids, item_ids):
    number_of_chunks_to_eat = NUMBER_OF_CHUNKS_TO_EAT

    for chunk in data_chunks:
        for index, row in chunk.iterrows():
            
            user = user_ids[row[USER_ID_COLUMN]]
            item = item_ids[row[ITEM_ID_COLUMN]]

            item_vector = item_matrix[item, :]
            user_vector = user_matrix[user, :]

            error = row[RATING_COLUMN] - predict(user, item, user_matrix, item_matrix, user_bias_vector, item_bias_vector, global_bias)

            item_vector = item_vector + LEARNING_RATE * (error * user_vector - REGULARIZATION * item_vector)
            user_vector = user_vector + LEARNING_RATE * (error * item_vector - REGULARIZATION * user_vector)
            user_bias_vector[user] = user_bias_vector[user] + LEARNING_RATE * (error * user_bias_vector[user] - REGULARIZATION * user_bias_vector[user])
            item_bias_vector[item] = item_bias_vector[item] + LEARNING_RATE * (error * item_bias_vector[item] - REGULARIZATION * item_bias_vector[item])

            for n in range(0, NUMBER_OF_FACTORS):
                item_matrix[item, n] = item_vector[n]
                user_matrix[user, n] = user_vector[n]

            if index%PRINT_EVERY == 0:
                print_verbose(f"training... at index: {index} error is {error}")

        number_of_chunks_to_eat -= 1
        if number_of_chunks_to_eat <= 0:
            break

def  mean_generic_error(generic, data_chunks, user_matrix, item_matrix, user_bias_vector, item_bias_vector, global_bias, user_ids, item_ids):
    number_of_chunks_to_eat = NUMBER_OF_CHUNKS_TO_EAT
    accumulator = 0
    count = 0

    for chunk in data_chunks:
        for index, row in chunk.iterrows():
            
            user = user_ids[row[USER_ID_COLUMN]]
            item = item_ids[row[ITEM_ID_COLUMN]]

            error = row[RATING_COLUMN] - predict(user, item, user_matrix, item_matrix, user_bias_vector, item_bias_vector, global_bias)
            
            accumulator += generic(error)
            count += 1

            if index%PRINT_EVERY == 0:
                print_verbose("calculating mean error... at index: {}".format(index))

        number_of_chunks_to_eat -= 1
        if number_of_chunks_to_eat <= 0:
            break

    return accumulator / count

def mean_absolute_error(data_chunks, user_matrix, item_matrix, user_bias_vector, item_bias_vector, global_bias, user_ids, item_ids):
    return mean_generic_error(abs, data_chunks, user_matrix, item_matrix, user_bias_vector, item_bias_vector, global_bias, user_ids, item_ids)

def mean_square_error(data_chunks, user_matrix, item_matrix, user_bias_vector, item_bias_vector, global_bias, user_ids, item_ids):
    return mean_generic_error(lambda x: x**2, data_chunks, user_matrix, item_matrix, user_bias_vector, item_bias_vector, global_bias, user_ids, item_ids)

class rating_prediction:
    index = 0
    prediction = 0
    
    def __init__(self, index, prediction):
        self.index = index
        self.prediction = prediction

    def __str__(self):
        return f"({self.prediction} @ {self.index})"

    def __repr__(self):
        return f"({self.prediction} @ {self.index})"

"""
    k: number of recommendations to make
"""
def recommend(user_vector, item_matrix, k):
    result = [rating_prediction(None, -math.inf) for _ in range(0, k)]

    minimum_value = result[0]

    for i, item_vector in enumerate(item_matrix):
        predicted = np.dot(user_vector, item_vector)
        if (predicted > minimum_value.prediction):
            result.remove(minimum_value)
            result.append(rating_prediction(i, predicted))
            minimum_value = min(result, key=lambda x: x.prediction)
    
    return result

def read_csv():
    return pd.read_csv(TRAIN_FILE_PATH, chunksize=CHUNK_SIZE, usecols=[USER_ID_COLUMN, ITEM_ID_COLUMN, RATING_COLUMN])

def get_test_set(test_dataframe):
	result = set()
	for _, row in test_dataframe.iterrows():
		result.add((row[USER_ID_COLUMN], row[ITEM_ID_COLUMN]))
	return result
    
if __name__ == "__main__":
    data_chunks = read_csv()

    print("Digesting....")
    user_ids, item_ids, uid_max, iid_max, global_bias = digest(data_chunks)
    print("-"*16)
    number_of_users = uid_max + 1
    number_of_items = iid_max + 1

    data_chunks = read_csv()

    print(f"global bias: {global_bias}")
    
    user_matrix = np.random.random((number_of_users, NUMBER_OF_FACTORS))
    item_matrix = np.random.random((number_of_items, NUMBER_OF_FACTORS))
    user_bias_vector = np.zeros(number_of_users)
    item_bias_vector = np.zeros(number_of_items)

    print("Training:")

    for i in range(0,  EPOCHS):
        data_chunks = read_csv()
        fit_model(data_chunks, user_matrix, item_matrix, user_bias_vector, item_bias_vector, global_bias, user_ids, item_ids)

        data_chunks = pd.read_csv(TRAIN_FILE_PATH, chunksize=CHUNK_SIZE)

        err = mean_square_error(data_chunks, user_matrix, item_matrix, user_bias_vector, item_bias_vector, global_bias, user_ids, item_ids)
        print (f"::::EPOCH {i}::::      Error: {err}")
    
    print("-"*16)
    print("Evaluating...")
    actual_user_ids = user_ids.keys() # The reader is asked to recall that user_ids is a dict that maps the actual ids to our own made-up sequential integer ids
    actual_item_ids = item_ids.keys()

    print("Reading test data.")
    test_dataframe = pd.read_csv(TEST_FILE_PATH, usecols=[USER_ID_COLUMN, ITEM_ID_COLUMN, RATING_COLUMN])
    test_set = get_test_set(test_dataframe)

    print("Calculating top-k results")
    prediction_doer = svd_prediction_doer(user_ids, item_ids, user_matrix, item_matrix, user_bias_vector, item_bias_vector, global_bias)
    top_10_ratings = topk.topKRatings(10, prediction_doer, actual_user_ids, actual_item_ids, mtype="svd")
    results = topk.topKMetrics(top_10_ratings, test_set, actual_user_ids, actual_item_ids)
    print(results)