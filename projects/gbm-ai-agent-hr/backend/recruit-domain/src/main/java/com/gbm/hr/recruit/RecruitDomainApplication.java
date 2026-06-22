package com.gbm.hr.recruit;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = {"com.gbm.hr.recruit", "com.gbm.hr.common"})
public class RecruitDomainApplication {
    public static void main(String[] args) {
        SpringApplication.run(RecruitDomainApplication.class, args);
    }
}
