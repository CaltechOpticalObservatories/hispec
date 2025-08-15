#include <iostream>         // for printing to console
#include <algorithm>        // for computing median (sort) and 2Dmax (max_element) and for (max)
#include <cmath>            // for computing STD (sqrt) and step limiter (copysign)
#include <cstdlib>          // for doing step limiter in code (abs)
#include <unistd.h>         // for sleep function
#include <signal.h>         // for ctrl-C handling (signal and SIGINT)
#include <chrono>           // for computing loop time
#include <map>              // for holding the goal positions (map)
#include <fstream>          // (ifstream, ofstream)
#include <sstream>          // (istringstream)
#include <string>           // (string)
#include <cstring>     
#include <thread>
#include <vector>
#include <numeric>


//Simple Timing test for getting 300 hz execution cadence.
double frequency = 2000;
int duration = 20;
int array_size = static_cast<int>(frequency * duration * 1.1);
// Use std::vector instead of a raw array
std::vector<long> time_stamps(array_size);
int main()
{
    //unneeded math here
    auto period = std::chrono::duration<double, std::milli>(1000.0 / frequency);

    //count tracker
    int count = 0;
    auto testTime = std::chrono::seconds(duration);

    //Start Timer
    auto start_t0 = std::chrono::high_resolution_clock::now();
    auto elapsed = std::chrono::high_resolution_clock::now() - start_t0;

    //External While loop for to replicate full execution cycle
    while(true)
    {
        //break when needed
        elapsed = std::chrono::high_resolution_clock::now() - start_t0;

        if (elapsed >= testTime) 
        {
            break;  // Exit the loop after 10 seconds
        }
        //internal while loop with sleeps to wait for execution
        while((std::chrono::high_resolution_clock::now()-start_t0) < (count*period))
        {
            std::this_thread::sleep_for(std::chrono::nanoseconds(500));
        }
        //print to array or command line, counter?
        auto now = std::chrono::high_resolution_clock::now();
        auto duration_in_microseconds = std::chrono::duration_cast<std::chrono::microseconds>(now.time_since_epoch());
        time_stamps[count] = duration_in_microseconds.count();
        count++;
    }
    std::cout << "Count over "<< duration <<" seconds(expect "<<(duration*frequency)<<"):" << count << std::endl;

    //Mean calculations
    std::vector<long> time_diffs(array_size);
    long sum = 0;
    long sumsq = 0;
    int N_rti = 0;
    long rti_outlier_tol = 2 * period.count();
    for(int i = 1; i < count; i++)
    {
        time_diffs[i] = time_stamps[i] - time_stamps[i-1]; 
        sum += time_diffs[i];
        sumsq += time_diffs[i] * time_diffs[i];
        if(time_diffs[i] > (period.count() + rti_outlier_tol))
        {
            //This counts the outliers, to get a better idea of accuracy of STD
            N_rti++;
        }
    }

    // Compute mean difference
    double mean = std::accumulate(time_diffs.begin(), time_diffs.end(), 0.0) / (count-1);

    std::cout << "Mean Loop time in Microseconds: " << mean << std::endl;

    //Standard Deviation Calculations
    double variance = (sumsq/(count-1))-(mean * mean);

    double final_std = std::sqrt(variance);

    std::cout << "Standard Diviation: " << final_std << std::endl;

    //Outluer count

    std::cout << "Counts Outside of RTIx2: " << N_rti << std::endl;
}