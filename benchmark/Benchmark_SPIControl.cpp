/**
 First Git Version of the FSM SPI-Control Benchmarking
 
 TODO: Finish updating header

 * Minimal test of the FT4222 Chip (using the dev board)
 * - lists all available FT devices
 * - connects to the first device
 * - configures that device to single-io SPI master mode
 * - Simultaneously read+writes 14 bytes (does this twice in a row)
 * - Disconnects from the device
 *
 * To Compile:
 * - g++ -o FT4222_BasicTest FT4222_BasicTest.cpp -L./ -lft4222 -Wl,-rpath=.
 *      NOTE: In the above, '-Wl,-rpath=.' tells the binary to look in the current dir for the necessary libraries
 * - ALT:  g++ -O2 -o FT4222_BasicTest_CLMove FT4222_BasicTest_Baseline.cpp -L./ -lft4222 -Wl,-rpath=.
 * 
 * To Run Test:
 *  - (must use sudo since hsdev is not part of the user group)
 *  - sudo ./FT4222_BasicTest
 *  - ALT: sudo chrt -f 50 ./FT4222_BasicTest_CLMove
 *
 * 
 */

#include <iostream>         // for printing to console
#include <string.h>           // for memset
#include <vector>           // Vectors to hold Bytes
#include <unistd.h>         // for sleep
#include <cstring>        // for memcpy
#include <chrono>
#include <thread>
#include <fstream>          // (ifstream, ofstream)

//------------------------------------------------------------------------------ 
// include FTDI libraries 
// 
#include "ftd2xx.h" 
#include "libft4222.h" 
std::vector< FT_DEVICE_LIST_INFO_NODE > g_FT4222DevList;
FT_STATUS ftStatus;
FT4222_STATUS ft4222Status;
unsigned char chipMode;

uint8 ssoMap_SS0O_PIN = 0x01;     // Used to denote that ss0o pin should be used


uint16 CRC_INIT = 0xFFFF;
uint16 CRC_POLY = 0x8005;
uint16 CRC_XOR  = 0x0000;

//------------------------------------------------------------------------------ 

/*************
    TODO: Edit this section to match test params
 **************/
 //Simple Timing test for getting 300 hz execution cadence.
double frequency = 5000;
// Variable to hold number of samples in Signal Test
int sigLength = 100000;
// Scaling factor for amplitude(Schroeder scale)*amplitude [0.5 = 1mRad]
float sigScale = 0.25;//[(35.0/10000.0) Schroeder scaling]*[real amplitude];
int testAxis = 0;// Determining what axis to send the signal (0 = x, 1 = y)
float lim[] ={2.0, 33.0};
//Filename for signal source
std::string signal_filename = "/home/hsdev/Documents/PDRDF/TestSignals/sine_5000sr_150hz.csv";
//save file with examples:
std::string path = "/home/hsdev/Documents/PDRDF/test_code/SPI_Chip_Testing/";//300,500,750,1000,1500
//ex: chirp_300hz_Ax0_0p5_try1.csv ; Schroeder_300hz_Ax0_0p5_try1.csv ; sine_300sr_5hz_Ax0_0p5_try1.csv
//std::string save_filename = "Sine_300sr_5hz_Ax0_0p5_try1.csv";
std::string save_filename = "FT4222_SPI_Sine_5000sr_AdnacoTest.csv";
std::string fullpath;
bool verbose = false;
bool noPrint = true;
/********
    TODO: Do not Edit pass here unless advised
 *********/

inline std::string DeviceFlagToString(DWORD flags) 
{ 
    std::string msg; 
    msg += (flags & 0x1) ? "DEVICE_OPEN" : "DEVICE_CLOSED"; 
    msg += ", "; 
    msg += (flags & 0x2) ? "High-speed USB" : "Full-speed USB"; 
    return msg; 
} 

const char* clockRateToString(FT4222_ClockRate rate)
{
    switch(rate) {
        case SYS_CLK_60: return "60 MHz";
        case SYS_CLK_24: return "24 MHz";
        case SYS_CLK_48: return "48 MHz";
        case SYS_CLK_80: return "80 MHz";
	default: return "Unknown clock rate";
    }
}


void ListFtUsbDevices() 
{
    FT_STATUS ftStatus = 0; 
 
    DWORD numOfDevices = 0; 
    ftStatus = FT_CreateDeviceInfoList(&numOfDevices); 
 
    for (DWORD iDev = 0; iDev < numOfDevices; ++iDev) 
    { 
        FT_DEVICE_LIST_INFO_NODE devInfo; 
        memset(&devInfo, 0, sizeof(devInfo)); 
 
        ftStatus = FT_GetDeviceInfoDetail(iDev, &devInfo.Flags, &devInfo.Type, 
        &devInfo.ID, &devInfo.LocId, 
        devInfo.SerialNumber, 
        devInfo.Description, 
        &devInfo.ftHandle); 
 
        if (FT_OK == ftStatus) 
        { 
            printf("Dev %d:\n", iDev); 
            printf("  Flags= 0x%x, (%s)\n", devInfo.Flags, 
            DeviceFlagToString(devInfo.Flags).c_str()); 
            printf("  Type= 0x%x\n", devInfo.Type); 
            printf("  ID= 0x%x\n", devInfo.ID); 
            printf("  LocId= 0x%x\n", devInfo.LocId); 
            printf("  SerialNumber= %s\n", devInfo.SerialNumber); 
            printf("  Description= %s\n", devInfo.Description); 
            printf("  ftHandle= 0x%p\n", devInfo.ftHandle); 
 
            const std::string desc = devInfo.Description; 
            if (desc.find("FT4222") != std::string::npos)
            { 
                g_FT4222DevList.push_back(devInfo); 
            } 
        } 
    } 
} 

int FT4222H_SPI_Init(int index, FT_HANDLE * ftHandle) 
{ 
    FT_STATUS ftStatus; 
    FT4222_STATUS ft4222Status; 
 
    ftStatus = FT_Open(index, ftHandle); 
    if (ftStatus != FT_OK) 
    { 
        printf("FT_Open failed (error code %d)\n", (int)ftStatus); 
        return -1; 
    } else {
        printf("Successefully opened index %d\n", index);
    }	

    unsigned char chipMode;

    ft4222Status = FT4222_GetChipMode(*ftHandle, &chipMode);
    if (FT4222_OK != ft4222Status)
    {
        printf("FT4222 Get Chip Mode failed\n");
    } else {
        printf("Current Chip Mode: %d\n", chipMode);
    }

    FT4222_ClockRate clk;
    ft4222Status = FT4222_GetClock(*ftHandle, &clk);
    if (FT4222_OK != ft4222Status)
    {
        printf("FT4222 master clock query failed\n");
        return -1;
    } else {
        printf("Current Master Clock rate: %s\n", clockRateToString(clk));
    }

    /* --- OPTIONAL - to try different System Clock Rates --- 
    FT4222_ClockRate newclk = SYS_CLK_60;
    ft4222Status = FT4222_SetClock(*ftHandle, newclk);
    if (FT4222_OK != ft4222Status)
    {
        printf("FT4222 setting master clock failed\n");
        return -1;
    } else {
        printf("Master Clock rate set to: %s\n", clockRateToString(newclk));
    }

    ft4222Status = FT4222_GetClock(*ftHandle, &clk);
    if (FT4222_OK != ft4222Status)
    {
        printf("FT4222 master clock query failed\n");
        return -1;
    } else {
        printf("New Master Clock rate queried: %s\n", clockRateToString(clk));
    }
    */

    // NOTE:: Setting anything other than CLK_NONE leads to a spurious
    	// pulse on the SCK, CS, and MOSI lines when the device is Init'd
    	// (I think this pulse is spawned when the chip turns on the clock division)
    // -- WARNING !! -- However, CLK_NONE is technically not supported,
        // so it leads to strange behavior. For example, the actual clock
	// rate will be whatever the last-used clock rate was, meaning you're
	// not actually setting the clock rate. Also, the clock rate will
	// change when you power cycle the device  
    ft4222Status = FT4222_SPIMaster_Init(*ftHandle, SPI_IO_SINGLE, CLK_DIV_4, CLK_IDLE_LOW, 
                            CLK_TRAILING, ssoMap_SS0O_PIN); 

    if (FT4222_OK != ft4222Status)
    {
        printf("FT4222 SPI Master Init failed\n");
        return -1;
    } else {
        printf("Successfully initialized SPI Master Interface\n");
    }

    sleep(1);

    return 0; 
} 

int FT4222H_UnInit(FT_HANDLE ftHandle) 
{
    FT4222_UnInitialize(ftHandle); 
    //ms = getms(); 
    FT_Close(ftHandle); 
    
    return 0; 
}  


/*********************************/
/**** START MESSAGE FORMATTERS ***/
/*********************************/
/**
 * Function: calculateCRC16(command)
 * Description: Does crc16 calculation based on initial and polynomial values
 * Parameters: full Hex values of move command(or bytes not sure yet) 
 * Return: CRC-16 calc in hex(or bytes)
 */
uint16 calculateCRC16(const uint8* cmd_pre, size_t length)
{

    uint16 crc = CRC_INIT;

    for (size_t i = 0; i < length; ++i) 
    {
        crc ^= static_cast<uint16_t>(cmd_pre[i])<<8;

        for (int bit = 0; bit < 8; ++bit) 
        {
            if (crc & 0x8000)
            {
                crc = (crc << 1) ^ CRC_POLY;
            } else
            {
                crc <<= 1;
            }
        }
    }
    return crc ^ CRC_XOR;
}

/**
 * Function: commandToBytes
 * Description: Takes full command and adds the x and y values as bytes
 * Parameters: Connection Parameters
 * Return: void
 */
void commandToBytes(uint8* cmd, bool closeSVO, float x, float y, bool verbose)
{
    // Set the servos to open vs closed
    if ( closeSVO ) 
    {
        cmd[3] = 0x03;
    } else {
        cmd[3] = 0x00;
    }

    // ASSUMING our system is little-endian, add the cmd positions
        // (implicitly converting from floats to hex in IEEE 754 format):
    uint8 x_bytes[4], y_bytes[4];

    std::memcpy(x_bytes, &x, sizeof(x));
    std::memcpy(y_bytes, &y, sizeof(y));

    // Now reverse the byte order since E-727 demands other endian-ness
        // Also put directly into cmd buffer
    for (int i = 0; i < 4; ++i) 
    {
        cmd[4 + i] = x_bytes[3-i];
        cmd[8 + i] = y_bytes[3-i];
    }

    // Compute CRC16 over first 12 bytes, and add to the cmd buffer
    uint16 crc = calculateCRC16(cmd, 12); 
    cmd[12] = static_cast<uint8>((crc >> 8) & 0xFF);    // High byte
    cmd[13] = static_cast<uint8>(crc & 0xFF);           // Low byte

    if ( verbose ) 
    {
        printf("Formatted message: ");
        for (int i = 0; i < 14; ++i)
        {
            printf("0x%02X ", cmd[i]);
        }
        printf("\n");
    }
}

void extractPosFromCMD(const uint8* cmd, float& x_out, float& y_out, bool verbose)
{
    // ASSUMES our system is little-endian
    uint8 x_bytes[4], y_bytes[4];

    for (int i = 0; i < 4; ++i) {
        x_bytes[i] = cmd[7 - i]; 
        y_bytes[i] = cmd[11 - i];
    }

    // Extract bytes 4-7 and 8-11, reversing the byte order again
    std::memcpy(&x_out, x_bytes, sizeof(x_out));
    std::memcpy(&y_out, y_bytes, sizeof(y_out));
    
    if (verbose)
    {
        printf("Float positions from message:\n");
        printf("x = %f\n", x_out);
        printf("y = %f\n", y_out);
    }
}


/*********************************/
/**** END MESSAGE FORMATTERS *****/
/*********************************/

// FEI FSM E-727 Very Basic Test
// Write our 14 byte command
// Read 14 simultaneous bytes
int FEI_FSM_ReadWrite(FT_HANDLE ftHandle, uint8* cmd, uint8* readData, bool verbose) 
{ 

    FT4222_STATUS ft4222Status; 
    uint16 sizeTransferred; 
    
    // --- SIMULTANEOUS READ and WRITE ---
    ft4222Status = FT4222_SPIMaster_SingleReadWrite(ftHandle, &readData[0], &cmd[0], 14, &sizeTransferred, true);

    if ( (ft4222Status != FT4222_OK) || (sizeTransferred != 14) )
    {
        printf("FT4222 SPI Master Single Read Write failed");
        std::cout << "sizeTransferred = " << sizeTransferred << " | Status = " << ft4222Status << std::endl;
        return -1;
    } else 
    {
        if ( verbose ) 
        {
            printf("Number of bytes written/read: %d\n", sizeTransferred);
        }
    }

    if ( verbose ) 
    {
        printf("Data Sent: ");
        for (int i = 0; i < sizeTransferred; ++i) 
        {
            printf("%x ", cmd[i]);
	}    
        printf("\n");
        printf("Data Read: ");
        for (int i = 0; i < sizeTransferred; ++i) 
        {
            printf("%x ", readData[i]);
        }    
        printf("\n");
    }

    return 0;


    /* 
    // --- SEQUENTIAL READ then WRITE ---
    // write 
    FT4222_SPIMaster_SingleWrite(ftHandle, cmd, 14, &sizeTransferred, false); 
    
    // then read 
    FT4222_SPIMaster_SingleRead(ftHandle, &readData[0], 20, &sizeTransferred, true); 
    printf("Data Read: ");
    for (int i = 0; i < sizeTransferred; ++i) 
    {
        printf("%x ", readData[i]);
    }    
    printf("\n");
    */
}

/*=====
 * Function to save an array into a CSV file
 ======*/
 void writeSignalCSV(double array[][6], const std::string& filename, int Nrows) 
 {
     /* This function saves arrays containing the results of a Signal Test (ie. hardcoded 7col) */
     fullpath = path + filename;
     std::cout << "Saving to: "<<fullpath<< std::endl;
     std::ofstream file(fullpath);
     
     if (!file.is_open()) 
     {
         std::cout << "Failed to open file: " << filename << std::endl;
         return;
     }
     
     // Get starting precision for the output stream
     int prec = file.precision();
 
     // Now print
     for ( int row = 0; row < Nrows; row++ ) 
     {
         // Print the timestamp with the dedicated formating to ensure no truncation
         file.precision(20);     // Set a large enough precision 
         file << array[row][0] << ",";
         file.precision(prec);   // Reset precision
         // Print the remaining columns using the default precision
         for ( int col = 1; col < 11; col++ ) 
         {
             if(6 < col && col < 10)
             {
                 file.precision(20);
                 file << array[row][col];
             }
             else
             {
                 file.precision(prec);
                 file << array[row][col];
             }
             //file << array[row][col];
             if (col != 11 - 1) 
             {
                 file << ",";
             }
         }
         file << "\n";
     }
     
     file.close();
     
     std::cout << "CSV file written successfully: " << filename << std::endl;
 }

//------------------------------------------------------------------------------ 
// main 
//------------------------------------------------------------------------------ 
int main(int argc, char const *argv[]) 
{ 
    
    // Find all FT4222 devices
    ListFtUsbDevices(); 
    
    if (g_FT4222DevList.empty()) 
    { 
        printf("No FT4222 device is found!\n"); 
	    return 0; 
    } 
    
    // Connect the SPI interface on index 0
    FT_HANDLE ftHandle1 = NULL;
    if (FT4222H_SPI_Init(0, &ftHandle1)){
        return 0;
    }


    // Declare the array with the message to be sent
    uint8 cmd[14] = {};
    uint8 ret_bytes[14] = {};
    // Format the constant part of the message
    cmd[0] = 0x10; // PID/ST
    cmd[1] = 0x02; // CTR/CNT (2 axes to be commanded)
    cmd[2] = 0x00; // Flags (part 1 - Nothing)

    // Format the message to send:
    bool closeSVO = true;
    float xgoal = 17.500f;
    float ygoal = 17.500f;
    float xout = 0.000f;
    float yout = 0.000f;

    //------------------Load Signal for injection-----------------------//
    // Declare relevant arrays for Signal test
    float SignalSig[sigLength];    
    double results[sigLength][6] = {};

    // Load test signal
    std::cout << " === Loading Inject Signal ===" << std::endl;
    std::cout << "signal filename: "<< signal_filename << std::endl;

    std::ifstream SignalFile;
    SignalFile.open(signal_filename);
    if (!SignalFile.is_open()) 
    {
        std::cerr << "Error: File could not be opened!" << std::endl;
    }
    for (int ctr = 0; ctr < sigLength; ctr++)
    {
        SignalFile >> SignalSig[ctr];
        SignalSig[ctr] = (SignalSig[ctr] * sigScale) + (35.0 / 2.0);
        // TODO:: Check limits and Exit program early if out of bounds 
        //std::cout << SignalSig[ctr] << std::endl;
        if ( (lim[0] > SignalSig[ctr]) | (lim[1] < SignalSig[ctr]) ) 
        {
            std::cout << "ERROR: Desired PI-position "<< ctr <<" in signal ( " << SignalSig[ctr] << " ) is out of range " << std::endl;
            exit(FT4222H_UnInit(ftHandle1));
        }
        //Make sure to close file and exit/close connection to mirror.
    }
    SignalFile.close();

    int otherAxis = 1;
    if (testAxis == 1)
    {
        otherAxis = 0;
    }

    
    // To avoid initial transients, set the FSM to first signal position
    // This also lets us close the SVO loops
    printf("Closing SVO loops and setting FSM to starting position\n");
    xgoal = 35.0/2.0;
    ygoal = 35.0/2.0;
    // Send two back-to-back OL commands
    commandToBytes(cmd, false, xgoal, ygoal, true);
    FEI_FSM_ReadWrite(ftHandle1, cmd, ret_bytes, true);
    sleep(0.33);
    FEI_FSM_ReadWrite(ftHandle1, cmd, ret_bytes, true);
    sleep(0.33);
    // Send FSM to starting position
    xgoal = SignalSig[0];
    ygoal = 35.0/2.0;
    commandToBytes(cmd, closeSVO, xgoal, ygoal, true);
    FEI_FSM_ReadWrite(ftHandle1, cmd, ret_bytes, true);
    sleep(0.33);
    FEI_FSM_ReadWrite(ftHandle1, cmd, ret_bytes, true);



    //-----------------Main Loop-----------------------------//
 
     std::cout << "===============================================" << std::endl;
     std::cout << "       Starting Loop " << std::endl;
 
     //Timing math and variables here
     auto period = std::chrono::duration<double, std::milli>(1000.0 / frequency);// turn into microseconds!
 
     // Save reference (0) timestamp for Signal signal
     auto Signal_t0 = std::chrono::high_resolution_clock::now();  
 
     // Loop iteration counter (needed for Signal Signal injection)
     int loopItr = -1;
 
 
     while (true) 
     {
        loopItr++;
        // For Signal or Timing Tests: exit loop after specific number of iterations
        if ( loopItr == sigLength ) 
        {
            break;
        }

        //Do prep work before image pull to reduce runtime between image and PI command as much as possible///

        if (verbose) { std::cout << "--- Iteration Start ---" << std::endl; }

        // Inject Signal signal rather than measured offset
        // To change axis, change between pos 0 and 1
        xgoal = SignalSig[loopItr];
        ygoal = 35.0/2.0;

        commandToBytes(cmd, closeSVO, xgoal, ygoal, false);

        while((std::chrono::high_resolution_clock::now()-Signal_t0) < (loopItr*period))
        {
            std::this_thread::sleep_for(std::chrono::nanoseconds(500));
        }
        
        // Record timestamp for Signal test immediately before move
        results[loopItr][0] = (double)std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::high_resolution_clock::now()-Signal_t0).count();
 
        // Send move to PI since we passed the limit checks
        FEI_FSM_ReadWrite(ftHandle1, cmd, ret_bytes,false);
        //MOV
        if (verbose) { std::cout << "PI moved to ( X=" << xgoal << " , Y=" << ygoal << " )" << std::endl; } 
        else if ( !noPrint ) { std::cout << " PI moved"; }

        results[loopItr][5] = (double)std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::high_resolution_clock::now()-Signal_t0).count();
        //qpos
        //Timing retrieval for Position query(read return bytes from controler and parse them)
        extractPosFromCMD(ret_bytes, xout, yout, false);

        //results[loopItr][6] = (double)std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::high_resolution_clock::now()-Signal_t0).count();
        // Record relevant information for Signal Test
        results[loopItr][1] = xgoal;
        results[loopItr][2] = ygoal;
        results[loopItr][3] = xout;
        results[loopItr][4] = yout;
    }
 
    // Save the ingject signal test results
    writeSignalCSV(results, save_filename, sigLength);

    // Clean up connection
    FT4222H_UnInit(ftHandle1);
    
    return 0; 
} 
