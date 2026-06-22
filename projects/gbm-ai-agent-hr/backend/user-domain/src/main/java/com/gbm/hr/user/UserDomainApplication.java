package com.gbm.hr.user;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = {"com.gbm.hr.user", "com.gbm.hr.common"})
public class UserDomainApplication {
    public static void main(String[] args) {
        SpringApplication.run(UserDomainApplication.class, args);
    }
}
