import subprocess
import time
import csv
# import socket

def execute_commands(commands):
    """Execute a list of shell commands."""

    for command in commands:
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                print(f"Command '{command}' executed successfully")
            else:
                print(f"Command '{command}' failed with exit code {process.returncode}.")
        except FileNotFoundError:
            print(f"Command '{command}' not found.")
        except Exception as e:
            print(f"An error occurred while executing '{command}': {e}")


def execute_timed_commands(commands, n, csv_filename="command_times.csv"):
    """
    Executes a list of shell commands
    """
    results = []

    start_total = time.time()
    for i in range(n):
        for command in commands:
            start_time = time.time()
            try:
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate()
                end_time = time.time()
                execution_time = end_time - start_time
                return_code = process.returncode

                print(f"  Command '{command}' executed in {execution_time:.4f} seconds")
                results.append([i + 1, command, execution_time, return_code])
                
            except FileNotFoundError:
                print(f"Command '{command}' not found.")
                results.append([i + 1, command, "Error", "Error"])
            except Exception as e:
                print(f"An error occurred while executing '{command}': {e}")
                results.append([i + 1, command, "Error", "Error"])
                

    end_total = time.time()
    total_execution_time = end_total - start_total
    print(f"Total time of {n} exposures (without prep): {total_execution_time:.4f} seconds.")

    with open(csv_filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Iteration", "Command", "Execution Time (seconds)", "Return Code"])
        writer.writerows(results)

if __name__ == "__main__":

    prep_commands = [
        "../camera-interface/bin/socksend -h localhost -p 3031 'open'",
        "../camera-interface/bin/socksend -h localhost -p 3031 'load'",
        "../camera-interface/bin/socksend -h localhost -p 3031 'power on'",
        "../camera-interface/bin/socksend -h localhost -p 3031 'setp Start 1'",
        "../camera-interface/bin/socksend -h localhost -p 3031 'exptime 0'",
        "../camera-interface/bin/socksend -h localhost -p 3031 'hsetup'",
        "../camera-interface/bin/socksend -h localhost -p 3031 'hroi 100 109 100 109'",
        "../camera-interface/bin/socksend -h localhost -p 3031 'hwindow 1'",
        "../camera-interface/bin/socksend -h localhost -p 3031 'zmq 1'"
        # "../camera-interface/bin/socksend -h localhost -p 3031 'autofetch 1'"
    ]

    take_exposures = [
        "../camera-interface/bin/socksend -h localhost -p 3031 'hexpose 1000'"
    ]

    execute_commands(prep_commands)
    execute_timed_commands(take_exposures, 1)
