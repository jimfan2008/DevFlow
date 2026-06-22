package com.gbm.hr.auto;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
@ComponentScan(basePackages = {"com.gbm.hr.auto", "com.gbm.hr.common"})
public class AutoDomainApplication {
    public static void main(String[] args) {
        SpringApplication.run(AutoDomainApplication.class, args);
    }
}
