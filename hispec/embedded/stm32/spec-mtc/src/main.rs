#![no_std]
#![no_main]

pub mod nucleo;

use nucleo::led;

use defmt::*;
use {defmt_rtt as _, panic_probe as _};
use embassy_executor::Spawner;

#[embassy_executor::main]
async fn main(spawner: Spawner) {
    info!("SPEC Multichannel Temperature Controller (Test)");

    let p = embassy_stm32::init(Default::default());

    debug!("Starting LED task");
    spawner.must_spawn(led::led_blink(p));
}
