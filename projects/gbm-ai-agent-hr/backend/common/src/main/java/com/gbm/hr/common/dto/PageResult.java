package com.gbm.hr.common.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 分页响应结果
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PageResult<T> {
    private List<T> items;
    private Long total;
    private Integer page;
    private Integer size;
    private Integer totalPages;

    public boolean hasNext() {
        return page < totalPages;
    }

    public boolean hasPrevious() {
        return page > 1;
    }
}
