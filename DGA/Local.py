from DGA.Algorithm import Genetic_Algorithm_Base as Algorithm, Genetic_Algorithm
from DGA.Model import Model
from DGA.Pool import Pool, Subset_Pool
from DGA.Server import list_public_attributes, LOG_DIR
from DGA.File_IO import write_log, AGENT_NAME
import os
from os.path import join as file_path


class Synchronized:
  def __init__(self, run_name: str, algorithm: Algorithm, model: Model, **kwargs):
    # Create run folder
    os.makedirs(file_path(run_name, LOG_DIR), exist_ok=True)

    # Re-initialize algorithm (necessary workaround from async version)
    algorithm_args = list_public_attributes(algorithm)
    algorithm_args = {key: algorithm.__dict__[key] for key in algorithm_args}
    alg_type = type(algorithm)

    # Initialize class vars
    self.run_name = run_name
    self.algorithm = alg_type(**algorithm_args, run_name=run_name)
    self.model = model
    self.pool = Pool()
    self.algorithm.pool = self.pool
    self.algorithm.pool.add_subset_pool(self.algorithm.valid_parents)
    self.log = []
    self.iteration = 0

    # Re-point passed in algorithm & model to properly initialized ones
    algorithm = self.algorithm
    model = self.model

    # Set logged vars for model
    model.log_vars = algorithm.log_vars

    # Load data for model
    model.load_data(**kwargs)

  def run(self):

    # Set history for agent 0
    if self.algorithm.history is not None:
      self.algorithm.history[0] = []

    # Loop until end condition met
    while not self.algorithm.end_condition():
      self.iteration += 1

      # Generate & test gene (+ update pool)
      gene_name, _ = self.algorithm.fetch_params(agent_id=0)
      fitness = self.model.run(self.pool[gene_name])
      self.pool[gene_name].set_fitness(fitness)
      self.pool[gene_name].set_tested(True)
      self.pool.update_subpools()   # Needed to manually update 'valid_parents' pool

      # Log & update history
      self.log.append(self.model.logger(self.pool[gene_name]))
      if self.algorithm.history is not None:
        self.algorithm.history[0].append(self.log[-1])

    # Write log to file
    # Set to model_0, implies only one model made whole run
    log_path = file_path(self.run_name, LOG_DIR, f"{AGENT_NAME}_0.log")
    with open(log_path, 'w') as log_file:
      for log in self.log:
        log_file.write(str(log) + "\n")
