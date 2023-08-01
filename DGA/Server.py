import os.path
import subprocess
import json
import pickle
from os.path import join as file_path
import portalocker
import sys
import argparse
import time
from DGA.pool_functions import write_gene

# Constants for filesystem
POOL_DIR = "pool"
LOG_DIR = "logs"
ARGS_FOLDER = "run_args"
POOL_LOCK_NAME = "POOL_LOCK.lock"

def write_args_to_file(client_id: int, **kwargs):
  args_path = file_path(kwargs['run_name'], ARGS_FOLDER, f"client{client_id}_args.pkl")
  kwargs['client_id'] = client_id
  pickle.dump(kwargs, open(args_path, 'wb'))


def load_args_from_file(client_id: int, run_name: str):
  args_path = file_path(run_name, ARGS_FOLDER, f"client{client_id}_args.pkl")
  return pickle.load(open(args_path, 'rb'))


class Server:
  def __init__(self, run_name: str, algorithm_path: str, algorithm_name: str, client_path: str, client_name: str,
               num_parallel_processes: int, iterations: int, call_type: str = 'init', **kwargs):
    sys.path.append('/'.join(algorithm_path.split('/')[0:-1]))
    sys.path.append('/'.join(client_path.split('/')[0:-1]))

    # Add path for algorithm and client to sys.path
    server_path = os.path.abspath(__file__)               # Get absolute path to current location on machine
    base_path = '/'.join(server_path.split('/')[0:-2])    # Get path to "./Distributed_GA" ie. base folder
    full_alg_path = file_path(base_path, '/'.join(algorithm_path.split('/')[0:-1]))     # Prepend to path stub passed by user script
    full_client_path = file_path(base_path, '/'.join(client_path.split('/')[0:-1]))
    sys.path.append(full_alg_path)
    sys.path.append(full_client_path)
    alg_module_name = algorithm_path.split('/')[-1][0:-3]
    client_module_name = algorithm_path.split('/')[-1][0:-3]

    # Load algorithm and client classes
    self.algorithm = getattr(__import__(alg_module_name, fromlist=[alg_module_name]), algorithm_name)
    self.client = getattr(__import__(client_module_name, fromlist=[client_module_name]), client_name)
    self.run_name = run_name
    self.algorithm_path = algorithm_path
    self.algorithm_name = algorithm_name
    self.client_path = client_path
    self.client_name = client_name
    self.num_parallel_processes = num_parallel_processes
    self.iterations = iterations
    self.server_file_path = server_path  # Note: CWD not the same as DGA folder

    # Switch for handling client, server, or run initialization
    if call_type == "init":
      self.init(**kwargs)
    elif call_type == "run_client":
      self.run_client(**kwargs)
    elif call_type == "server_callback":
      self.server_callback(**kwargs)
    else:
      raise Exception(f"error, improper call_type: {call_type}")

  def init(self, **kwargs):
    # Make directory if needed
    # Note: CWD will be at where user-written script is
    os.makedirs(file_path(self.run_name, POOL_DIR), exist_ok=True)
    os.makedirs(file_path(self.run_name, LOG_DIR), exist_ok=True)
    os.makedirs(file_path(self.run_name, ARGS_FOLDER), exist_ok=True)

    # Generate initial 10 genes
    alg = self.algorithm(run_name=self.run_name, **kwargs)
    init_genes = []
    for i in range(self.num_parallel_processes):
      init_genes.append(alg.fetch_gene())

    # Call 1 client for each gene (and initialize count for iterations)
    count = 0
    for i, (g_name, _) in enumerate(init_genes):
      self.make_call(i, g_name, "run_client", count, **kwargs)

  def run_client(self, **kwargs):
    # Run gene
    gene_name = kwargs['gene_name']
    clnt = self.client(self.run_name, gene_name)
    fitness = clnt.run()

    # Return fitness (by writing to files)
    gene_data = clnt.gene_data
    gene_data['fitness'] = fitness
    gene_data['status'] = 'tested'
    pool_lock_path = file_path(self.run_name, POOL_LOCK_NAME)
    with portalocker.Lock(pool_lock_path, timeout=100) as _:
      write_gene(gene_data, gene_name, self.run_name)

      # Write gene to logs
      timestamp = time.strftime('%H:%M:%S', time.localtime())
      log_data = {'timestamp': timestamp, 'gene_name': gene_name, 'gene_data': gene_data}
      self.write_logs(self.run_name, kwargs['client_id'], log_data)  # Separate logs by client_id

    # Callback server
    self.make_call(call_type="server_callback", **kwargs)   # Other args contained in kwargs

  def server_callback(self, **kwargs):
    count = kwargs.pop('count')
    iterations = self.iterations
    count += 1
    if count >= iterations:
      sys.exit()

    # Lock pool during gene creation
    pool_lock_path = file_path(self.run_name, POOL_LOCK_NAME)
    while True:
      with portalocker.Lock(pool_lock_path, timeout=100) as _:

        # Init alg (loads gene pool)
        alg = self.algorithm(run_name=self.run_name, **kwargs)

        # Fetch next gene for testing
        gene_name, success = alg.fetch_gene()

      # Break if fetch was success, otherwise loops
      if success:
        break
      else:
        time.sleep(1)

    # Remove old gene_name from args, and send new gene to client
    kwargs.pop('gene_name')
    self.make_call(call_type="run_client", gene_name=gene_name, count=count, **kwargs)

  def write_logs(self, run_name: str, log_name: int, log_data: dict):

    # TODO: temporary solution, make this more general
    log_data['gene_data']['gene'] = log_data['gene_data']['gene'].tolist()

    log_path = file_path(run_name, LOG_DIR, str(log_name)) + ".log"
    with open(log_path, 'a') as log_file:
      log_file.write(json.dumps(log_data) + "\n")

  def make_call(self, client_id: int, gene_name: str, call_type: str, count: int, **kwargs):
    write_args_to_file(client_id=client_id,
                       gene_name=gene_name,
                       call_type=call_type,   # callback or run_client
                       count=count,           # current iteration
                       run_name=self.run_name,
                       algorithm_path=self.algorithm_path,
                       algorithm_name=self.algorithm_name,
                       client_path=self.client_path,
                       client_name=self.client_name,
                       num_parallel_processes=self.num_parallel_processes,
                       iterations=self.iterations,
                       **kwargs)

    # Run command according to OS
    # TODO: SOMEONE DO THIS FOR MAC PLEASE
    if sys.platform == "linux":
      p = subprocess.Popen(["python3", self.server_file_path, f"--run_name={self.run_name}", f"--client_id={client_id}"])
    elif sys.platform == "win32":
      p = subprocess.Popen(["python", self.server_file_path, f"--run_name={self.run_name}", f"--client_id={client_id}"],
                         shell=True)
    elif sys.platform == "darwin":
      pass    # MAC HANDLING



# Main function catches server-callbacks & runs clients
if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--client_id', type=int)
  parser.add_argument('--run_name', type=str)
  args = parser.parse_args()

  # Load args from file
  all_args = load_args_from_file(args.client_id, args.run_name)

  # Run server protocol with bash kwargs
  Server(**all_args)