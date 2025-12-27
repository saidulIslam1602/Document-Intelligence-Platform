#!/usr/bin/env python3
"""
Production Performance & Optimization Checker
Verifies all optimizations are in place and working
"""

import requests
import time
import psutil
import sys
from typing import Dict, Any, List
from colorama import init, Fore, Style

init(autoreset=True)

class PerformanceChecker:
    """Check production readiness and performance"""
    
    def __init__(self, api_url: str = "http://localhost:8003"):
        self.api_url = api_url
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = 0
    
    def print_header(self, title: str):
        """Print section header"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}{title}")
        print(f"{Fore.CYAN}{'='*60}")
    
    def print_check(self, name: str, passed: bool, details: str = ""):
        """Print check result"""
        if passed:
            print(f"{Fore.GREEN}✅ {name}")
            self.checks_passed += 1
        else:
            print(f"{Fore.RED}❌ {name}")
            self.checks_failed += 1
        
        if details:
            print(f"   {Fore.YELLOW}{details}")
    
    def print_warning(self, message: str):
        """Print warning"""
        print(f"{Fore.YELLOW}⚠️  {message}")
        self.warnings += 1
    
    def check_service_health(self) -> bool:
        """Check if services are healthy"""
        self.print_header("Service Health Checks")
        
        services = [
            ("API Gateway", f"{self.api_url}/health"),
            ("Frontend", "http://localhost:80/health"),
            ("Prometheus", "http://localhost:9090/-/healthy"),
        ]
        
        all_healthy = True
        for name, url in services:
            try:
                response = requests.get(url, timeout=5)
                is_healthy = response.status_code == 200
                self.print_check(
                    f"{name} is healthy",
                    is_healthy,
                    f"Status: {response.status_code}"
                )
                all_healthy = all_healthy and is_healthy
            except Exception as e:
                self.print_check(f"{name} is accessible", False, str(e))
                all_healthy = False
        
        return all_healthy
    
    def check_response_times(self) -> bool:
        """Check API response times"""
        self.print_header("Response Time Checks")
        
        endpoints = [
            ("/health", 100),  # Should be < 100ms
            ("/api/documents", 500),  # Should be < 500ms
        ]
        
        all_fast = True
        for endpoint, threshold_ms in endpoints:
            try:
                start = time.time()
                response = requests.get(f"{self.api_url}{endpoint}", timeout=5)
                latency_ms = (time.time() - start) * 1000
                
                is_fast = latency_ms < threshold_ms
                self.print_check(
                    f"{endpoint} responds quickly",
                    is_fast,
                    f"{latency_ms:.0f}ms (threshold: {threshold_ms}ms)"
                )
                all_fast = all_fast and is_fast
            except Exception as e:
                self.print_check(f"{endpoint} accessible", False, str(e))
                all_fast = False
        
        return all_fast
    
    def check_caching(self) -> bool:
        """Check if caching is working"""
        self.print_header("Caching Checks")
        
        try:
            # First request (cache miss)
            start1 = time.time()
            response1 = requests.get(f"{self.api_url}/api/documents", timeout=5)
            latency1 = (time.time() - start1) * 1000
            
            # Second request (should be cached)
            start2 = time.time()
            response2 = requests.get(f"{self.api_url}/api/documents", timeout=5)
            latency2 = (time.time() - start2) * 1000
            
            # Cached request should be faster
            is_cached = latency2 < latency1 * 0.8  # At least 20% faster
            self.print_check(
                "Caching is working",
                is_cached,
                f"1st: {latency1:.0f}ms, 2nd: {latency2:.0f}ms"
            )
            
            return is_cached
        except Exception as e:
            self.print_check("Caching functional", False, str(e))
            return False
    
    def check_compression(self) -> bool:
        """Check if gzip compression is enabled"""
        self.print_header("Compression Checks")
        
        try:
            response = requests.get(
                "http://localhost:80",
                headers={'Accept-Encoding': 'gzip'},
                timeout=5
            )
            
            is_compressed = 'gzip' in response.headers.get('Content-Encoding', '')
            self.print_check(
                "Gzip compression enabled",
                is_compressed,
                f"Content-Encoding: {response.headers.get('Content-Encoding', 'none')}"
            )
            
            return is_compressed
        except Exception as e:
            self.print_check("Compression check", False, str(e))
            return False
    
    def check_security_headers(self) -> bool:
        """Check security headers"""
        self.print_header("Security Header Checks")
        
        try:
            response = requests.get("http://localhost:80", timeout=5)
            headers = response.headers
            
            required_headers = [
                'X-Frame-Options',
                'X-Content-Type-Options',
                'X-XSS-Protection',
            ]
            
            all_present = True
            for header in required_headers:
                is_present = header in headers
                self.print_check(
                    f"{header} present",
                    is_present,
                    f"Value: {headers.get(header, 'missing')}"
                )
                all_present = all_present and is_present
            
            return all_present
        except Exception as e:
            self.print_check("Security headers", False, str(e))
            return False
    
    def check_resource_usage(self) -> bool:
        """Check system resource usage"""
        self.print_header("Resource Usage Checks")
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        cpu_ok = cpu_percent < 80
        memory_ok = memory.percent < 80
        disk_ok = disk.percent < 80
        
        self.print_check(
            "CPU usage is healthy",
            cpu_ok,
            f"{cpu_percent}% (threshold: 80%)"
        )
        
        self.print_check(
            "Memory usage is healthy",
            memory_ok,
            f"{memory.percent}% (threshold: 80%)"
        )
        
        self.print_check(
            "Disk usage is healthy",
            disk_ok,
            f"{disk.percent}% (threshold: 80%)"
        )
        
        return cpu_ok and memory_ok and disk_ok
    
    def check_database_indexes(self) -> bool:
        """Check if database indexes are applied"""
        self.print_header("Database Optimization Checks")
        
        try:
            response = requests.get(f"{self.api_url}/admin/db-stats", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                indexes_count = data.get('indexes_count', 0)
                has_indexes = indexes_count > 0
                
                self.print_check(
                    "Database indexes applied",
                    has_indexes,
                    f"{indexes_count} indexes found"
                )
                
                return has_indexes
            else:
                self.print_warning("Database stats endpoint not available")
                return False
        except Exception as e:
            self.print_warning(f"Could not check database indexes: {e}")
            return False
    
    def check_monitoring(self) -> bool:
        """Check if monitoring is configured"""
        self.print_header("Monitoring Checks")
        
        try:
            # Check if metrics endpoint exists
            response = requests.get(f"{self.api_url}/metrics", timeout=5)
            has_metrics = response.status_code == 200
            
            self.print_check(
                "Metrics endpoint available",
                has_metrics,
                f"Status: {response.status_code}"
            )
            
            # Check Prometheus
            try:
                prom_response = requests.get("http://localhost:9090/-/healthy", timeout=5)
                prom_healthy = prom_response.status_code == 200
                self.print_check("Prometheus is running", prom_healthy)
            except:
                self.print_check("Prometheus is running", False)
                prom_healthy = False
            
            return has_metrics or prom_healthy
        except Exception as e:
            self.print_check("Monitoring configured", False, str(e))
            return False
    
    def run_all_checks(self):
        """Run all performance and optimization checks"""
        print(f"{Fore.CYAN}{Style.BRIGHT}")
        print("╔════════════════════════════════════════════════════════════╗")
        print("║   Production Performance & Optimization Checker            ║")
        print("╚════════════════════════════════════════════════════════════╝")
        
        # Run all checks
        self.check_service_health()
        self.check_response_times()
        self.check_caching()
        self.check_compression()
        self.check_security_headers()
        self.check_resource_usage()
        self.check_database_indexes()
        self.check_monitoring()
        
        # Print summary
        self.print_header("Summary")
        total_checks = self.checks_passed + self.checks_failed
        success_rate = (self.checks_passed / total_checks * 100) if total_checks > 0 else 0
        
        print(f"{Fore.GREEN}Passed: {self.checks_passed}")
        print(f"{Fore.RED}Failed: {self.checks_failed}")
        print(f"{Fore.YELLOW}Warnings: {self.warnings}")
        print(f"{Fore.CYAN}Success Rate: {success_rate:.1f}%")
        
        if self.checks_failed == 0:
            print(f"\n{Fore.GREEN}{Style.BRIGHT}🎉 All checks passed! Your application is production-ready!")
            return 0
        else:
            print(f"\n{Fore.RED}{Style.BRIGHT}⚠️  Some checks failed. Please review and fix issues.")
            return 1


if __name__ == "__main__":
    checker = PerformanceChecker()
    exit_code = checker.run_all_checks()
    sys.exit(exit_code)

