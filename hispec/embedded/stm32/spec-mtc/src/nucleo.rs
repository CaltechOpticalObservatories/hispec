pub mod led;

use embassy_stm32::Config;
use embassy_stm32::gpio::{AnyPin, Pin};
use embassy_stm32::rcc::{mux, AHBPrescaler, APBPrescaler, HSIPrescaler, Pll, PllDiv, PllMul, PllPreDiv, PllSource, Sysclk, VoltageScale};

pub struct Board {
    pub led_green: AnyPin,
    pub led_orange: AnyPin,
    pub led_red: AnyPin,
}

impl Board {
    pub fn new() -> Self {
        let mut config = Config::default();
        config.rcc.hsi = Some(HSIPrescaler::DIV1);
        config.rcc.csi = true;
        config.rcc.pll1 = Some(Pll {
            source: PllSource::HSI,
            prediv: PllPreDiv::DIV4,
            mul: PllMul::MUL25,
            divp: Some(PllDiv::DIV2),
            divq: Some(PllDiv::DIV4),
            divr: None,
        });
        config.rcc.pll2 = Some(Pll {
            source: PllSource::HSI,
            prediv: PllPreDiv::DIV4,
            mul: PllMul::MUL25,
            divp: None,
            divq: None,
            divr: Some(PllDiv::DIV4),
        });
        config.rcc.sys = Sysclk::PLL1_P;
        config.rcc.ahb_pre = AHBPrescaler::DIV1;
        config.rcc.apb1_pre = APBPrescaler::DIV2;
        config.rcc.apb2_pre = APBPrescaler::DIV2;
        config.rcc.apb3_pre = APBPrescaler::DIV2;
        config.rcc.voltage_scale = VoltageScale::Scale1;
        config.rcc.mux.adcdacsel = mux::Adcdacsel::PLL2_R;

        let p = embassy_stm32::init(config);

        let led_green = p.PB0.degrade();
        let led_orange = p.PF4.degrade();
        let led_red = p.PG4.degrade();

        Self {
            led_green,
            led_orange,
            led_red,
        }
    }
}