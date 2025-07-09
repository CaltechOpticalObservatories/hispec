use defmt::debug;
use {defmt_rtt as _, panic_probe as _};
use embassy_stm32::Peripherals;
use embassy_stm32::gpio::{Level, Output, Speed};
use embassy_time::Timer;

#[embassy_executor::task]
pub async fn led_blink(mut p: Peripherals) {
    let mut ld1 = Output::new(&mut p.PB0, Level::High, Speed::Low);
    let mut ld2 = Output::new(&mut p.PF4, Level::High, Speed::Low);
    let mut ld3 = Output::new(&mut p.PG4, Level::High, Speed::Low);

    debug!("Turning LD1 on (Green LED)");
    ld1.set_high();
    debug!("Turning LD2 on (Yellow LED)");
    ld2.set_high();
    debug!("Turning LD3 on (Red LED)");
    ld3.set_high();

    Timer::after_secs(5).await;

    debug!("Turning LEDs off");
    ld1.set_low();
    ld2.set_low();
    ld3.set_low();
}
