#include <new>
#include <string>
#include <vector>


//===========================================================================
#define DECLARE_DEFAULTER_CLASS(type, tname)                                \
class tname##_defaulter {                                                   \
public:                                                                     \
    tname##_defaulter(type a = 11, type b = 22, type c = 33);               \
                                                                            \
public:                                                                     \
    type m_a, m_b, m_c;                                                     \
};
DECLARE_DEFAULTER_CLASS(short, short)   // for testing of default arguments
DECLARE_DEFAULTER_CLASS(unsigned short, ushort)
DECLARE_DEFAULTER_CLASS(int, int)
DECLARE_DEFAULTER_CLASS(unsigned, uint)
DECLARE_DEFAULTER_CLASS(long, long)
DECLARE_DEFAULTER_CLASS(unsigned long, ulong)
DECLARE_DEFAULTER_CLASS(long long, llong)
DECLARE_DEFAULTER_CLASS(unsigned long long, ullong)
DECLARE_DEFAULTER_CLASS(float, float)
DECLARE_DEFAULTER_CLASS(double, double)


//===========================================================================
class base_class {                 // for simple inheritance testing
public:
    base_class() { m_b = 1; m_db = 1.1; }
    virtual ~base_class() {}
    virtual int get_value() { return m_b; }
    double get_base_value() { return m_db; }

    virtual base_class* cycle(base_class* b) { return b; }
    virtual base_class* clone() { return new base_class; }

    virtual void* mask(void* p) { return p; }

public:
    int m_b;
    double m_db;
};

class derived_class : public base_class {
public:
    derived_class() { m_d = 2; m_dd = 2.2;}
    virtual int get_value() { return m_d; }
    double get_derived_value() { return m_dd; }
    virtual base_class* clone() { return new derived_class; }

public:
    int m_d;
    double m_dd;
};


//===========================================================================
class a_class {                    // for esoteric inheritance testing
public:
    a_class() { m_a = 1; m_da = 1.1; }
    ~a_class() {}
    virtual int get_value() = 0;

public:
    int m_a;
    double m_da;
};

class b_class : public virtual a_class {
public:
    b_class() { m_b = 2; m_db = 2.2;}
    virtual int get_value() { return m_b; }

public:
    int m_b;
    double m_db;
};

class c_class_1 : public virtual a_class, public virtual b_class {
public:
    c_class_1() { m_c = 3; }
    virtual int get_value() { return m_c; }

public:
    int m_c;
};

class c_class_2 : public virtual b_class, public virtual a_class {
public:
    c_class_2() { m_c = 3; }
    virtual int get_value() { return m_c; }

public:
    int m_c;
};

typedef c_class_2 c_class;

class d_class : public virtual c_class, public virtual a_class {
public:
    d_class() { m_d = 4; }
    virtual int get_value() { return m_d; }

public:
    int m_d;
};

a_class* create_c1();
a_class* create_c2();

int get_a(a_class& a);
int get_b(b_class& b);
int get_c(c_class& c);
int get_d(d_class& d);


//===========================================================================
namespace a_ns {                   // for namespace testing
    extern int g_a;
    int get_g_a();

    struct b_class {
        b_class() { m_b = -2; }
        int m_b;
        static int s_b;

        struct c_class {
            c_class() { m_c = -3; }
            int m_c;
            static int s_c;
        };
    };

    namespace d_ns {
        extern int g_d;
        int get_g_d();

        struct e_class {
            e_class() { m_e = -5; }
            int m_e;
            static int s_e;

            struct f_class {
                f_class() { m_f = -6; }
                int m_f;
                static int s_f;
            };
        };

    } // namespace d_ns

} // namespace a_ns


//===========================================================================
template<typename T>               // for template testing
class T1 {
public:
    T1(T t = T(1)) : m_t1(t) {}
    T get_value() { return m_t1; }

public:
    T m_t1;
};

template<typename T>
class T2 {
public:
    T2(T t = T(2)) : m_t2(t) {}
    T get_value() { return m_t2; }

public:
    T m_t2;
};

template<typename T, typename U>
class T3 {
public:
    T3(T t = T(3), U u = U(33)) : m_t3(t), m_u3(u) {}
    T get_value_t() { return m_t3; }
    U get_value_u() { return m_u3; }

public:
    T m_t3;
    U m_u3;
};

namespace a_ns {

    template<typename T>
    class T4 {
    public:
        T4(T t = T(4)) : m_t4(t) {}
        T get_value() { return m_t4; }

    public:
        T m_t4;
    };

} // namespace a_ns

extern template class T1<int>;
extern template class T2<T1<int> >;
extern template class T3<int, double>;
extern template class T3<T1<int>, T2<T1<int> > >;
extern template class a_ns::T4<int>;
extern template class a_ns::T4<a_ns::T4<T3<int, double> > >;


//===========================================================================
// for checking pass-by-reference of builtin types
void set_int_through_ref(int& i, int val);
int pass_int_through_const_ref(const int& i);
void set_long_through_ref(long& l, long val);
long pass_long_through_const_ref(const long& l);
void set_double_through_ref(double& d, double val);
double pass_double_through_const_ref(const double& d);


//===========================================================================
class some_abstract_class {        // to test abstract class handling
public:
    virtual void a_virtual_method() = 0;
};

class some_concrete_class : public some_abstract_class {
public:
    virtual void a_virtual_method() {}
};


//===========================================================================
class ref_tester {                 // for assignment by-ref testing
public:
    ref_tester() : m_i(-99) {}
    ref_tester(int i) : m_i(i) {}
    ref_tester(const ref_tester& s) : m_i(s.m_i) {}
    ref_tester& operator=(const ref_tester& s) {
        if (&s != this) m_i = s.m_i;
        return *this;
    }
    ~ref_tester() {}

public:
    int m_i;
};


//===========================================================================
class some_convertible {           // for math conversions testing
public:
    some_convertible() : m_i(-99), m_d(-99.) {}

    operator int()    { return m_i; }
    operator long()   { return m_i; }
    operator double() { return m_d; }

public:
    int m_i;
    double m_d;
};


class some_comparable {
};

bool operator==(const some_comparable& c1, const some_comparable& c2 );
bool operator!=( const some_comparable& c1, const some_comparable& c2 );


//===========================================================================
extern double my_global_double;    // a couple of globals for access testing
extern double my_global_array[500];
extern double* my_global_ptr;
static const char my_global_string[] = "aap " " noot " " mies";

//===========================================================================
class some_class_with_data {       // for life-line and identity testing
public:
    class some_data {
    public:
        some_data()                 { ++s_num_data; }
        some_data(const some_data&) { ++s_num_data; }
        ~some_data()                { --s_num_data; }

        static int s_num_data;
    };

    some_class_with_data gime_copy() {
        return *this;
    }

    const some_data& gime_data() { /* TODO: methptrgetter const support */
        return m_data;
    }

    int m_padding;
    some_data m_data;
};


//===========================================================================
class pointer_pass {               // for testing passing of void*'s
public:
    long gime_address_ptr(void* obj) {
        return (long)obj;
    }

    long gime_address_ptr_ptr(void** obj) {
        return (long)*((long**)obj);
    }

    long gime_address_ptr_ref(void*& obj) {
        return (long)obj;
    }

    static long set_address_ptr_ptr(void** obj) {
        (*(long**)obj) = (long*)0x4321;
        return 42;
    }

    static long set_address_ptr_ref(void*& obj) {
        obj = (void*)0x1234;
        return 21;
    }
};


//===========================================================================
class multi1 {                     // for testing multiple inheritance
public:
    multi1(int val) : m_int(val) {}
    virtual ~multi1();
    int get_multi1_int() { return m_int; }

private:
    int m_int;
};

class multi2 {
public:
    multi2(int val) : m_int(val) {}
    virtual ~multi2();
    int get_multi2_int() { return m_int; }

private:
    int m_int;
};

class multi : public multi1, public multi2 {
public:
    multi(int val1, int val2, int val3) :
        multi1(val1), multi2(val2), m_int(val3) {}
    virtual ~multi();
    int get_my_own_int() { return m_int; }

private:
    int m_int;
};


//===========================================================================
class new_overloader {             // for testing calls to overloaded new
public:
    static int s_instances;

public:
    void* operator new(std::size_t size);
    void* operator new(std::size_t, void* p) throw();
    void operator delete(void* p, std::size_t size);
};


//===========================================================================
template<class T>                  // more template testing
class my_templated_class {
public:
    T m_b;
};

template<class T>
T my_templated_function(T t) { return t; }

template class my_templated_class<std::vector<float> >;
template char my_templated_function<char>(char);
template double my_templated_function<double>(double);


//===========================================================================
class overload_one_way {           // overload order testing
public:
    int gime() const;
    std::string gime();
};

class overload_the_other_way {
public:
   std::string gime();
   int gime() const;
};
