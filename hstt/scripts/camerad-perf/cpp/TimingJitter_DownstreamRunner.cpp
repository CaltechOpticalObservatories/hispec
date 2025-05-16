#include <zmq.hpp>
#include <iostream>
#include <chrono>       // computing loop time (and sleep)
#include <fstream>      // saving csv file
#include <thread>

// Conversion Constants
int NS2US = 1e-3;       // nanosecond to microsecond conversion
int NS2SEC = 1e-9;      // nanosecond to second conversion

// User Inputs
int Nsamp = 10000;      // Size of preallocated timestamps array (max number of samples)
bool isPrint = false;   // Flag to print receive messages to terminal

int main(int argc, char** argv) {

    // Get filename for csv output, or note that we should just run local statistics
    bool isSaveCSV;
    std::string filename;
    if ( argc > 1 ) 
    {    
        isSaveCSV = true;
        std::cout << "Filename provided. Will save timestamps to: ";
        filename = argv[1];
        std::cout << filename << std::endl;
    } else {
        isSaveCSV = false;
        std::cout << "No Filename Provided... Will only print statistics" << std::endl;
    }

    // Preallocate output array
    long results[Nsamp] = {};

    // Create a ZeroMQ context
    zmq::context_t context(1);

    // Create an XSUB socket
    zmq::socket_t socket(context, zmq::socket_type::xsub);

    // Connect the socket to xpub
    socket.connect("tcp://localhost:5555");

    // Subscribe to all topics
    zmq::message_t subscribe_msg(1);
    memcpy(subscribe_msg.data(), "\x01", 1);
    socket.send(subscribe_msg, zmq::send_flags::none);

    std::cout << "Listening for messages on port 5555..." << std::endl;

    // Get starting timestamp
    auto t0 = std::chrono::high_resolution_clock::now();

    for (int sInd = 0; sInd < Nsamp; sInd++ ) {
        zmq::message_t message;
        socket.recv(message, zmq::recv_flags::none);
        //results[sInd] = std::chrono::duration<double>(std::chrono::high_resolution_clock::now()-t0).count();
        results[sInd] = std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::high_resolution_clock::now()-t0).count();

        // std::cout << sInd << std::endl;

        std::this_thread::sleep_for(std::chrono::microseconds(1));

        if ( isPrint ) { 
            std::string received(static_cast<char*>(message.data()), message.size());
            std::cout << "data received: " << received << std::endl; 
        }
    }

    // Save CSV with timestamps
    if ( isSaveCSV ) {
        
        std::cout << "Saving to : " << filename << std::endl;

        std::ofstream csvFile(filename);
        if ( csvFile.is_open() ) {
            // Get starting precision for the output stream
            int prec = csvFile.precision();

            // Set precision high enough to record nanosecond time
            csvFile.precision(15);

            for (int sInd = 0; sInd < Nsamp; sInd++ ) {
                csvFile << results[sInd] << "\n";
                //std::cout << sInd << " : " << results[sInd] << std::endl;
            }
            csvFile.close();
        } else {
            std::cerr << "Unable to open CSV file for writing." << std::endl;
        }
    }

    return 0;
}
