package com.gbm.hr.payroll;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
@ComponentScan(basePackages = {"com.gbm.hr.payroll", "com.gbm.hr.common"})
public class PayrollDomainApplication {
    public static void main(String[] args) {
        SpringApplication.run(PayrollDomainApplication.class, args);
    }
}
