import { useApi } from './useApi'
import { dashboardService } from '../services/apiServices'

export function useMLStatus() {
  const { data, loading } = useApi(dashboardService.getStats)

  return {
    hasInventory:      (data?.total_products  || 0) > 0,
    hasMLPredictions:  (data?.total_forecasted || 0) > 0,
    hasSalesData:      (data?.total_sales      || 0) > 0,
    totalProducts:     data?.total_products  || 0,
    lowStockCount:     data?.low_stock_count || 0,
    revenueToday:      data?.revenue_today   || 0,
    totalForecasted:   data?.total_forecasted || 0,
    loading,
  }
}