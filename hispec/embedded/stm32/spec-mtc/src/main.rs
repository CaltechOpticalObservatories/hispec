#![no_std]
#![no_main]

pub mod nucleo;
use cortex_m::delay;
use nucleo::{Board, led};

use defmt::*;
use {defmt_rtt as _, panic_probe as _};
use embassy_executor::Spawner;

#[embassy_executor::main]
async fn main(spawner: Spawner) {
    debug!("SPEC Multichannel Temperature Controller Firmware");
    let board = Board::new();

    let delay_sec: u64 = 2;
    spawner.spawn(led::blink(board.led_green, delay_sec)).unwrap();
}
