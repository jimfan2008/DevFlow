package com.gbm.hr.common.dto;

import lombok.Data;

/**
 * 分页请求参数 (page 从 1 开始)
 */
@Data
public class PageRequest {
    private Integer page = 1;
    private Integer size = 20;
    private String sortBy;
    private String order = "asc";
}
