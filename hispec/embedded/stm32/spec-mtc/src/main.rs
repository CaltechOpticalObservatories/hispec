#![no_std]
#![no_main]

use defmt::*;
use {defmt_rtt as _, panic_probe as _};
use embassy_executor::Spawner;
use embassy_stm32::gpio::{Level, Output, Speed};
use embassy_time::Timer;

#[embassy_executor::main]
async fn main(_spawner: Spawner) {
    info!("SPEC Multichannel Temperature Controller (Test)");

    let p = embassy_stm32::init(Default::default());

    let mut ld1 = Output::new(p.PB0, Level::High, Speed::Low);

    info!("Turning LD1 on (Green LED)");
    ld1.set_high();

    Timer::after_secs(5).await;

    info!("Turning LD1 off (Green LED)");
    ld1.set_low();
}
