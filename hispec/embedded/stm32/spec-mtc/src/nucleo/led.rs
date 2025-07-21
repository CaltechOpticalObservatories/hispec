use defmt::debug;
use {defmt_rtt as _, panic_probe as _};
use embassy_stm32::gpio::{AnyPin, Level, Output, Speed};
use embassy_time::Timer;

#[embassy_executor::task(pool_size = 3)]
pub async fn blink(led_p: AnyPin, delay_sec: u64) {
    let mut led = Output::new(led_p, Level::High, Speed::Low);

    loop {
        debug!("Turning LED on");
        led.set_high();
        Timer::after_secs(delay_sec).await;

        debug!("Turning LED off");
        led.set_low();
        Timer::after_secs(delay_sec).await;
    }
}
