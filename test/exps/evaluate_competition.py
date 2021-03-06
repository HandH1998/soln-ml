import os
import sys
import argparse
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor
from sklearn.metrics import make_scorer

sys.path.append(os.getcwd())
from solnml.utils.data_manager import DataManager
from solnml.components.evaluators.rgs_evaluator import RegressionEvaluator
from solnml.components.feature_engineering.fe_pipeline import FEPipeline

parser = argparse.ArgumentParser()
parser.add_argument('--time_limit', type=int, default=1800)
parser.add_argument('--algo', type=str, default='lightgbm', choices=['lightgbm', 'catboost_gpu', 'catboost_cpu'])
parser.add_argument('--task_id', type=int, default=3)
parser.add_argument('--train_size', type=float, default=1.0)
parser.add_argument('--data_dir', type=str, default='/Users/thomasyoung/PycharmProjects/AI_anti_plague/')
args = parser.parse_args()
time_limit = args.time_limit
data_dir = args.data_dir
task_id = args.task_id
train_size = args.train_size
regressor_id = args.algo


def smape(y_true, y_pred):
    sample_size = len(y_pred)
    numerator = np.abs(y_pred - y_true)
    denominator = (np.abs(y_pred) + np.abs(y_true)) / 2 + 1e-6
    return np.sum(np.divide(numerator, denominator)) / sample_size


class LightGBMRegressor():
    def __init__(self, n_estimators, learning_rate, num_leaves, min_child_weight,
                 subsample, colsample_bytree, reg_alpha, reg_lambda):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.subsample = subsample
        self.reg_alpha = reg_alpha
        self.reg_lambda = reg_lambda
        self.min_child_weight = min_child_weight
        self.colsample_bytree = colsample_bytree

        self.n_jobs = -1
        self.estimator = None

    def fit(self, X, y, metric=smape):
        self.estimator = LGBMRegressor(num_leaves=self.num_leaves,
                                       learning_rate=self.learning_rate,
                                       n_estimators=self.n_estimators,
                                       objective='regression',
                                       min_child_weight=self.min_child_weight,
                                       subsample=self.subsample,
                                       colsample_bytree=self.colsample_bytree,
                                       reg_alpha=self.reg_alpha,
                                       reg_lambda=self.reg_lambda,
                                       n_jobs=self.n_jobs
                                       )
        self.estimator.fit(X, y)
        return self

    def predict(self, X):
        return self.estimator.predict(X)


def create_csv(task_id=3):
    import pandas as pd
    train_data = pd.read_csv(data_dir + 'data/candidate_train.csv')
    train_answer = pd.read_csv(data_dir + 'data/train_answer.csv')
    print('complete dataset loading...')
    train_data = train_data.merge(train_answer, on='id', how='left')
    train_raw_data = train_data.iloc[:, 0:3177]

    label = train_data['p%d' % task_id]
    result = pd.concat([train_raw_data, label], axis=1).reset_index(drop=True)
    result.to_csv(data_dir + 'data/p%s.csv' % task_id, index=False)
    print(result.head())

    if not os.path.exists(data_dir + 'data/test_data.csv'):
        test_data = pd.read_csv(data_dir + 'data/candidate_val.csv')
        test_raw_data = test_data.iloc[:, 0:3177]
        test_raw_data.to_csv(data_dir + 'data/test_data.csv', index=False)
        print(test_raw_data.head())


def fetch_data(task_id):
    dm = DataManager()
    train_data_path = data_dir + 'data/p%d.csv' % task_id
    test_data_path = data_dir + 'data/test_data.csv'
    if not os.path.exists(train_data_path) or not os.path.exists(test_data_path):
        create_csv(task_id)

    train_data_node = dm.load_train_csv(train_data_path, label_col=-1, header='infer', sep=',')
    print('loading train data finished.')

    test_data_node = dm.load_test_csv(test_data_path, has_label=False, header='infer', sep=',')
    print('loading test data finished.')
    return train_data_node, test_data_node


def test_evaluator():
    config = {'colsample_bytree': 0.7214005546233202,
              'estimator': 'lightgbm',
              'learning_rate': 0.20740875048979773,
              'min_child_weight': 5,
              'n_estimators': 424,
              'num_leaves': 82,
              'reg_alpha': 0.001268145413023973,
              'reg_lambda': 0.15002466116267585,
              'subsample': 0.8110820196868197}
    config.pop('estimator', None)
    gbm = LightGBMRegressor(**config)
    scorer = make_scorer(smape, greater_is_better=False)
    raw_data, _ = fetch_data(task_id)
    evaluator = RegressionEvaluator(None, scorer, data_node=raw_data, name='fe', seed=1, estimator=gbm)
    print(evaluator(None))


def evaluation_based_feature_engineering(time_limit, seed=1):
    if task_id == 3 and regressor_id == 'lightgbm':
        config = {'colsample_bytree': 0.556390018826356,
                  'estimator': 'lightgbm',
                  'learning_rate': 0.027650212980431577,
                  'min_child_weight': 4,
                  'n_estimators': 1000,  # 2493,
                  'num_leaves': 818,
                  'reg_alpha': 0.00012695064964599962,
                  'reg_lambda': 0.0006320421481400761,
                  'subsample': 0.5611631795995178}
    elif task_id == 1 and regressor_id == 'lightgbm':
        config = {'colsample_bytree': 0.5836692544286752,
                  'estimator': 'lightgbm',
                  'learning_rate': 0.025011125056624308,
                  'min_child_weight': 3,
                  'n_estimators': 1000,  # 2000,
                  'num_leaves': 958,
                  'reg_alpha': 0.00025307513851761005,
                  'reg_lambda': 0.01911305077512719,
                  'subsample': 0.7850946965061745
                  }
    elif task_id == 3 and regressor_id == 'catboost_gpu':
        config = {'loss_function': 'RMSE',
                  'task_type': 'GPU',
                  'bootstrap_type': 'Poisson',
                  'learning_rate': 0.07215105304885769,
                  'n_estimators': 10000,
                  'min_child_samples': 7,
                  'max_depth': 8,
                  'reg_lambda': 4.084654778260157e-06,
                  'subsample': 0.9998568450178255
                  }
    elif task_id == 1 and regressor_id == 'catboost_gpu':
        config = {'loss_function': 'RMSE',
                  'task_type': 'GPU',
                  'bootstrap_type': 'Poisson',
                  'learning_rate': 0.030167431274216235,
                  'n_estimators': 10000,
                  'min_child_samples': 2,
                  'max_depth': 11,
                  'reg_lambda': 0.00010924008880152775,
                  'subsample': 0.9996005646983249
                  }
    else:
        raise ValueError("Hyperparameters not available!")

    config.pop('estimator', None)
    if regressor_id == 'lightgbm':
        estimator = LightGBMRegressor(**config)
    elif 'catboost' in regressor_id:
        estimator = CatBoostRegressor(**config)
    scorer = make_scorer(smape, greater_is_better=False)
    evaluator = RegressionEvaluator(None, scorer, name='fe', seed=seed, estimator=estimator)
    train_data, test_data = fetch_data(task_id)

    X, y = train_data.data
    idxs = np.arange(X.shape[0])
    np.random.shuffle(idxs)
    sample_size = int(X.shape[0] * train_size)
    subset_ids = idxs[:sample_size]
    X, y = X.iloc[subset_ids, :], y[subset_ids]
    train_data.data = [X, y]
    print(train_data)
    """
    nystronem_sampler: 15 bad
    kitchen_sinks: 13 bad
    random_trees_embedding: 18 bad
    feature_agglomeration_decomposer: 11 timeout.
    """
    # TODO: fast_ica, kernel_pca, and polynomial_features.
    # trans_used = [0, 3, 4, 5, 12, 16, 19, 30, 31, 32]
    # trans_used = [0, 3, 4, 5, 10, 11, 12, 16, 17, 19]
    # trans_used = [17, 30, 31]
    # trans_used = [30]
    pipeline = FEPipeline(task_type='regression', task_id='anti_plague',
                          fe_enabled=True, optimizer_type='eval_base',
                          time_budget=time_limit, evaluator=evaluator,
                          seed=seed, model_id='lightgbm',
                          time_limit_per_trans=900,
                          trans_set=None
                          )
    transformed_train_data = pipeline.fit_transform(train_data)
    print(pipeline.optimizer.get_incumbent_path())
    print('final train data shape & score', transformed_train_data.shape, transformed_train_data.score)
    transformed_test_datanode = pipeline.transform(test_data)
    print('final test data shape', transformed_test_datanode.shape)

    # Save results.
    np.save(data_dir + 'data/transformed_train_x-%d.csv' % task_id, transformed_train_data.data[0])
    np.save(data_dir + 'data/transformed_train_y-%d.csv' % task_id, transformed_train_data.data[1])
    np.save(data_dir + 'data/transformed_test-%d.csv' % task_id, transformed_test_datanode.data[0])


if __name__ == "__main__":
    # test_evaluator()
    evaluation_based_feature_engineering(time_limit)
