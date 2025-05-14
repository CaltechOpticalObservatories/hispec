#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <sys/wait.h>
#include <unistd.h>
#include <thread>
#include <filesystem>

std::string getSocksendPath() {
    std::filesystem::path exePath = std::filesystem::canonical("/proc/self/exe");
    std::filesystem::path baseDir = exePath.parent_path();
    std::filesystem::path socksendPath = baseDir / "../../camera-interface/bin/socksend";
    return std::filesystem::canonical(socksendPath).string();
}

std::string executeCommand(const std::string& command) {
    std::string result;
    FILE* pipe = popen(command.c_str(), "r");
    if (!pipe) {
        return "Error: Could not execute command.";
    }
    char buffer[128];
    while (!feof(pipe)) {
        if (fgets(buffer, 128, pipe) != nullptr) {
            result += buffer;
        }
    }
    pclose(pipe);
    return result;
}

int executeCommandWithReturnCode(const std::string& command) {
    int status = system(command.c_str());
    if (WIFEXITED(status)) {
        return WEXITSTATUS(status);
    } else {
        return -1;
    }
}

void executeCommands(const std::vector<std::string>& commands) {
    for (const auto& command : commands) {
        int returnCode = executeCommandWithReturnCode(command);
        if (returnCode == 0) {
            std::cout << "Command '" << command << "' executed successfully" << std::endl;
        } else {
            std::cout << "Command '" << command << "' failed with exit code " << returnCode << "." << std::endl;
        }
    }
}

void executeTimedCommands(const std::vector<std::string>& commands, int n, const std::string& csvFilename = "command_times.csv") {
    std::vector<std::vector<std::string>> results;
    auto startTotal = std::chrono::high_resolution_clock::now();

    for (int i = 0; i < n; ++i) {
        for (const auto& command : commands) {
            auto startTime = std::chrono::high_resolution_clock::now();
            int returnCode = executeCommandWithReturnCode(command);
            auto endTime = std::chrono::high_resolution_clock::now();
            std::chrono::duration<double> duration = endTime - startTime;
            double executionTime = duration.count();

            std::cout << "  Command '" << command << "' executed in " << executionTime << " seconds" << std::endl;
            std::stringstream ss;
            ss << i + 1;
            results.push_back({ss.str(), command, std::to_string(executionTime), std::to_string(returnCode)});
        }
    }

    auto endTotal = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> totalDuration = endTotal - startTotal;
    double totalExecutionTime = totalDuration.count();
    std::cout << "Total time of " << n << " exposures (without prep): " << totalExecutionTime << " seconds." << std::endl;

    std::ofstream csvFile(csvFilename);
    if (csvFile.is_open()) {
        csvFile << "Iteration,Command,Execution Time (seconds),Return Code\n";
        for (const auto& row : results) {
            for (size_t j = 0; j < row.size(); ++j) {
                csvFile << row[j];
                if (j < row.size() - 1) {
                    csvFile << ",";
                }
            }
            csvFile << "\n";
        }
        csvFile.close();
    } else {
        std::cerr << "Unable to open CSV file for writing." << std::endl;
    }
}

int main() {
    std::string socksend = getSocksendPath();
    std::vector<std::string> prepCommands = {
        socksend + " -h localhost -p 3031 'open'",
        socksend + " -h localhost -p 3031 'load'",
        socksend + " -h localhost -p 3031 'power on'",
        socksend + " -h localhost -p 3031 'setp Start 1'",
        socksend + " -h localhost -p 3031 'exptime 0'",
        socksend + " -h localhost -p 3031 'hsetup'",
        socksend + " -h localhost -p 3031 'hroi 51 60 51 60'",
        socksend + " -h localhost -p 3031 'hwindow 1'",
        // socksend + " -h localhost -p 3031 'zmq 1'",
        socksend + " -h localhost -p 3031 'autofetch 1'"
    };

    std::vector<std::string> takeExposures = {
        socksend + " -h localhost -p 3031 'hexpose 5000'"
        // socksend + " -h localhost -p 3031 'test timer 100 50'"
    };

    executeCommands(prepCommands);
    executeTimedCommands(takeExposures, 1);

    // std::this_thread::sleep_for(std::chrono::seconds( 2 ));
    // executeCommandWithReturnCode("../../camera-interface/bin/socksend -h localhost -p 3031 'abort'");

    return 0;
}

